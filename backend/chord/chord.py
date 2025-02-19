import asyncio
import fcntl
import hashlib
import pickle
import logging
import socket
import ssl
import struct
import time
import os
from uuid import uuid4
from typing import List, Optional
from pydantic import BaseModel


from chord.chord_messages import (
    CheckFileRequest,
    GenericResponse,
    JoinRequestMessage,
    JoinResponse,
    MessageContent,
    PingResponse,
    PredRequestMessage,
    PredResponse,
    SendFileRequest,
    SuccRequestMessage,
    SuccResponse,
    UpdateFTableRequest,
    UpdatePredRequestMessage,
    UpdateSuccRequestMessage,
)

PING_INTERVAL = 3  # seconds

MULTICAST_PORT = 2222

UPDATE_FTABLE_REQUEST = "UPDATE_FTABLE_REQUEST"
JOIN_REQUEST = "JOIN_REQUEST"
SUCC_REQUEST = "SUCC_REQUEST"
PRED_REQUEST = "PRED_REQUEST"
UPDATE_PRED_REQUEST = "UPDATE_PRED_REQUEST"
UPDATE_SUCC_REQUEST = "UPDATE_SUCC_REQUEST"
RESPONSE = "RESPONSE"
PING = "PING"
ADOPTION_REQUEST = "ADOPTION_REQUEST"
UPDATE_ALL_FTABLES_REQUEST = "UPDATE_ALL_FTABLES_REQUEST"
MULTICAST = "MULTICAST"
CHECK_FILE = "CHECK_FILE"
FILE_SEND_REQUEST = "FILE_SEND_REQUEST"


CHORD_MESSAGE_TYPES = [
    JOIN_REQUEST,
    RESPONSE,
    SUCC_REQUEST,
    UPDATE_FTABLE_REQUEST,
    PRED_REQUEST,
    UPDATE_PRED_REQUEST,
    UPDATE_SUCC_REQUEST,
    PING,
    ADOPTION_REQUEST,
    UPDATE_ALL_FTABLES_REQUEST,
    MULTICAST,
    CHECK_FILE,
    FILE_SEND_REQUEST,
]


class ChordMessage:
    def __init__(
        self, message_type: str, source_id: int, ring_signature: str, content: BaseModel
    ) -> None:
        self.message_type: str = message_type
        self.content: BaseModel = content
        self.ring_signature: str = ring_signature
        self.source_id: int = source_id

    def __str__(self) -> str:
        return (
            f"ChordMessage(\n"
            f"  Message Type: {self.message_type}\n"
            f"  Source ID: {self.source_id}\n"
            f"  Content: {self.content.model_dump_json()}\n"
            f")"
        )

    def encode(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def decode(message: bytes) -> Optional["ChordMessage"]:
        try:
            res = pickle.loads(message)

            if type(res) is not ChordMessage:
                return None

            return res
        except Exception:
            return None


class ChordNodeReference:
    def __init__(
        self, ip_address: str, port: int, node_id: int, id_bitlen: int = 32
    ) -> None:
        self.ip_address: str = ip_address
        self.port: int = port
        self.node_id: int = node_id
        self.id_bitlen: int = id_bitlen


class FingerTable(list[ChordNodeReference]):
    def __init__(
        self, node_ref: ChordNodeReference, id_bitlen: int = 32, *args, **kwargs
    ) -> None:
        super().__init__([node_ref] * id_bitlen, *args, **kwargs)

        self.node_id: int = node_ref.node_id
        self.id_bitlen: int = id_bitlen

    def __str__(self) -> str:
        res = "Address\tPort\tid\n"
        for entry in self:
            res += f"{entry.ip_address}\t{entry.port}\t{entry.node_id}\n"
        return res


class ChordNode:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton function
        if cls._instance is None:
            cls._instance = super(ChordNode, cls).__new__(cls)
            cls._instance.__init__(*args, **kwargs)
        return cls._instance

    def __init__(
        self,
        ip_address: str = "localhost",
        port: int = 4321,
        node_id: int = 0,
        id_bitlen: int = 32,
        is_debug: bool = False,
        file_path: str = "/app/data/audios",  # Assume here all filenames are the id's
    ) -> None:
        if not hasattr(self, "initialized"):
            self.ip_address = ip_address
            self.port = port
            self.node_id = node_id
            self.id_bitlen = id_bitlen

            self.ring_signature = uuid4().hex

            self.auto_ref = ChordNodeReference(ip_address, port, node_id, id_bitlen)

            self.succesor = self.predecessor = self.auto_ref
            self.finger_table = FingerTable(self.auto_ref, self.id_bitlen)

            logging.basicConfig(level=logging.DEBUG if is_debug else logging.INFO)
            self.logger = logging.getLogger(__name__)

            self.must_update_ftables = False

            self.file_path = file_path

            self.initialized = True

    async def listen(self) -> None:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        with open("ssl_cert/password", "r") as pswrd:
            password = pswrd.read()

        ssl_context.load_cert_chain(
            certfile="ssl_cert/cert.pem",
            keyfile="ssl_cert/key.pem",
            password=password,
        )

        server = await asyncio.start_server(
            self.handle_connection, self.ip_address, self.port, ssl=ssl_context
        )
        async with server:
            self.logger.info(
                f"Node {self.node_id} listening on {self.ip_address}:{self.port} with TLS"
            )
            await server.serve_forever()

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await reader.read(1024)
            message = ChordMessage.decode(data)
            if message:
                self.logger.debug(
                    f"Received message from node {message.source_id} of type {message.message_type}."
                )
                await self.handle_message(message, reader, writer)
            else:
                self.logger.debug("Received invalid message")
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            self.logger.debug(f"Some error occured while handling message: {e}")

    async def stabilize(self) -> None:
        last_entry = self.succesor
        last_entry_succ = self.succesor

        while True:
            await asyncio.sleep(PING_INTERVAL)

            if self.must_update_ftables:
                await self.update_all_finger_tables()

            if self.succesor.node_id != self.node_id:
                self.logger.debug(
                    f"Sending ping to successor node. [{self.predecessor.node_id}] -> [{self.node_id}] -> [{self.succesor.node_id}]"
                )

                succ_response = await self.ping_node(self.succesor)

                if not succ_response:
                    self.logger.warning("Successor node died, stibilizing...")

                    has_backup = await self.ping_node(last_entry)

                    self.succesor = last_entry if has_backup else last_entry_succ

                    await self.request_update_predecessor(last_entry, self.auto_ref)

                    await self.update_all_finger_tables(
                        (self.node_id + 1) % (1 << self.id_bitlen),
                        self.succesor.node_id,
                        self.succesor,
                    )

                    self.logger.info("STABILIZING DONE!")

                else:
                    _, last_entry = succ_response
                    succ_response = await self.ping_node(last_entry)

                    if succ_response:
                        _, last_entry_succ = succ_response

                    self.logger.debug("Checking for file backups...")

                    replicants = await self.get_replicants(3)

                    for replicant in replicants:
                        for file in os.listdir(self.file_path):
                            file_id = os.path.basename(file)
                            if not file_id.isalnum():
                                continue

                            file_id_node = int(file_id, 16) % (1 << self.id_bitlen)

                            if not is_between(
                                file_id_node, self.node_id, self.succesor.node_id
                            ):
                                continue

                            if not await self.check_file(file_id, replicant):
                                self.logger.debug(
                                    f"Backing up file {file_id} on node {replicant.node_id}."
                                )
                                await self.send_file(file_id, replicant)
                                self.logger.debug("Backup done!")

                    self.logger.debug("Everything all right!")

    async def start(self) -> None:
        await asyncio.gather(
            self.listen(),
            self.stabilize(),
            self.start_discovery_server(),
        )

    async def handle_message(
        self,
        message: ChordMessage,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        ms_type = message.message_type
        if ms_type == JOIN_REQUEST:
            assert isinstance(message.content, JoinRequestMessage)

            if message.content.my_id < 0 or message.content.my_id >= (
                2 << self.id_bitlen
            ):
                await self.send_message(
                    RESPONSE,
                    GenericResponse(is_success=False, message="Your Id is not valid."),
                    reader=reader,
                    writer=writer,
                )

            succesor = await self.find_successor(message.content.my_id)

            if succesor.node_id == message.content.my_id:
                await self.send_message(
                    RESPONSE,
                    GenericResponse(
                        is_success=False, message="Your Id is already being used."
                    ),
                    reader=reader,
                    writer=writer,
                )

            predecessor = await self.find_predecessor(message.content.my_id)

            new_node_ref = ChordNodeReference(
                message.content.my_ip_address,
                message.content.my_port,
                message.content.my_id,
            )

            await self.request_update_successor(predecessor, new_node_ref)
            await self.request_update_predecessor(succesor, new_node_ref)

            await self.send_message(
                RESPONSE,
                JoinResponse(
                    is_success=True,
                    message="Welcome to the fellowship of the Chord.",
                    succ_ip_address=succesor.ip_address,
                    succ_port=succesor.port,
                    succ_node_id=succesor.node_id,
                    pred_ip_address=predecessor.ip_address,
                    pred_port=predecessor.port,
                    pred_node_id=predecessor.node_id,
                ),
                reader=reader,
                writer=writer,
            )

        elif ms_type == ADOPTION_REQUEST:
            if self.predecessor.node_id == self.node_id == self.succesor.node_id:
                self.ring_signature = message.ring_signature

                await self.send_message(
                    RESPONSE,
                    GenericResponse(is_success=True),
                    reader=reader,
                    writer=writer,
                )
            else:
                await self.send_message(
                    RESPONSE,
                    GenericResponse(
                        is_success=False,
                        message="This node has a family, it cannot be adopted.",
                    ),
                    reader=reader,
                    writer=writer,
                )

        elif self.ring_signature != message.ring_signature:
            await self.send_message(
                RESPONSE,
                GenericResponse(
                    is_success=False,
                    message="The provided signature is not valid.",
                ),
                reader=reader,
                writer=writer,
                omit_signature=True,
            )

        elif ms_type == SUCC_REQUEST:
            assert isinstance(message.content, SuccRequestMessage)
            succesor = await self.find_successor(message.content.target_id)

            success = True

            if not isinstance(message.content, SuccRequestMessage):
                success = False

            await self.send_message(
                RESPONSE,
                SuccResponse(
                    is_success=success,
                    ip_address=succesor.ip_address,
                    port=succesor.port,
                    node_id=succesor.node_id,
                ),
                reader=reader,
                writer=writer,
            )

        elif ms_type == PRED_REQUEST:
            assert isinstance(message.content, PredRequestMessage)

            await self.send_message(
                RESPONSE,
                PredResponse(
                    is_success=True,
                    ip_address=self.predecessor.ip_address,
                    port=self.predecessor.port,
                    node_id=self.predecessor.node_id,
                ),
                reader=reader,
                writer=writer,
            )

        elif ms_type == UPDATE_FTABLE_REQUEST:
            assert isinstance(message.content, UpdateFTableRequest)

            new_responsible = ChordNodeReference(
                message.content.new_responsible_ip_address,
                message.content.new_responsible_port,
                message.content.new_responsible_node_id,
            )

            await self.update_finger_table_static(
                message.content.from_index,
                message.content.to_index,
                new_responsible,
            )

            self.ring_signature = message.content.new_signature

            await self.send_message(
                RESPONSE,
                SuccResponse(
                    is_success=True,
                    ip_address=self.succesor.ip_address,
                    port=self.succesor.port,
                    node_id=self.succesor.node_id,
                ),
                reader=reader,
                writer=writer,
            )

        elif ms_type == UPDATE_SUCC_REQUEST:
            assert isinstance(message.content, UpdateSuccRequestMessage)

            self.succesor = ChordNodeReference(
                message.content.new_succ_ip_address,
                message.content.new_succ_port,
                message.content.new_succ_node_id,
            )

        elif ms_type == UPDATE_PRED_REQUEST:
            assert isinstance(message.content, UpdatePredRequestMessage)

            self.predecessor = ChordNodeReference(
                message.content.new_pred_ip_address,
                message.content.new_pred_port,
                message.content.new_pred_node_id,
            )

        elif ms_type == PING:
            await self.send_message(
                RESPONSE,
                PingResponse(
                    is_success=True,
                    message="Still alive.",
                    succ_ip_address=self.succesor.ip_address,
                    succ_port=self.succesor.port,
                    succ_node_id=self.succesor.node_id,
                    pred_ip_address=self.predecessor.ip_address,
                    pred_port=self.predecessor.port,
                    pred_node_id=self.predecessor.node_id,
                ),
                reader=reader,
                writer=writer,
            )

        elif ms_type == UPDATE_ALL_FTABLES_REQUEST:
            self.must_update_ftables = True
            await self.send_message(
                RESPONSE,
                GenericResponse(is_success=True),
                reader=reader,
                writer=writer,
            )
        elif ms_type == CHECK_FILE:
            assert isinstance(message.content, CheckFileRequest)

            filename = f"{self.file_path}/{message.content.file_id}"

            success = os.path.exists(filename) and os.path.isfile(filename)

            await self.send_message(
                RESPONSE,
                GenericResponse(
                    is_success=success,
                    message="File found." if success else "File not found.",
                ),
                reader=reader,
                writer=writer,
            )
        elif ms_type == FILE_SEND_REQUEST:
            assert isinstance(message.content, SendFileRequest)

            await self.send_message(
                RESPONSE,
                GenericResponse(is_success=True),
                reader=reader,
                writer=writer,
            )

            await self.receive_file(
                message.content.file_id,
                message.content.file_size,
                writer,
                reader,
            )

    async def send_message(
        self,
        message_type: str,
        message_content: BaseModel,
        target_ip: str | None = None,
        target_port: int | None = None,
        target_id: int | None = None,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
        omit_signature: bool = False,
        force_get_response: bool = False,
    ) -> ChordMessage | None:
        assert message_type.upper() in CHORD_MESSAGE_TYPES
        assert target_id is None or target_id < (
            2 << self.id_bitlen
        )  # Equivalent to 2 ^ (x + 1) but faster

        message = ChordMessage(
            message_type,
            self.node_id,
            self.ring_signature if not omit_signature else "",
            message_content,
        )
        message_encoded = message.encode()

        clean = False

        try:
            if (not reader or not writer) and (target_ip and target_port):
                reader, writer, clean = await self.get_sending_stream(
                    target_ip, target_port
                )

            assert writer
            assert reader

            writer.write(message_encoded)
            await writer.drain()

            if clean:
                response = await reader.read(1024)
                writer.close()
                await writer.wait_closed()

                response = ChordMessage.decode(response)
                return response
            elif force_get_response:
                response = await reader.read(1024)
                response = ChordMessage.decode(response)
                return response

        except Exception as e:
            self.logger.debug(f"Failed to send message: {e}")

    async def get_sending_stream(
        self, target_ip: str, target_port: int
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, bool]:
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.load_verify_locations(cafile="ssl_cert/cert.pem")

        ssl_context.check_hostname = False

        reader, writer = await asyncio.open_connection(
            target_ip, target_port, ssl=ssl_context
        )
        clean = True
        return reader, writer, clean

    async def request_join(
        self, target_ip: str, target_port: int, target_id: int
    ) -> None:
        message_content = JoinRequestMessage(
            my_ip_address=self.ip_address,
            my_port=self.port,
            my_id=self.node_id,
            my_id_bitlen=self.id_bitlen,
        )

        response = await self.send_message(
            JOIN_REQUEST,
            message_content,
            target_ip,
            target_port,
            target_id,
        )

        assert response
        assert isinstance(response.content, JoinResponse)

        if response.content.is_success:
            self.succesor = ChordNodeReference(
                response.content.succ_ip_address,
                response.content.succ_port,
                response.content.succ_node_id,
            )

            self.predecessor = ChordNodeReference(
                response.content.pred_ip_address,
                response.content.pred_port,
                response.content.pred_node_id,
            )

            self.ring_signature = response.ring_signature

            await self.update_all_finger_tables()

            self.logger.info("Successfully joined to network!")
        else:
            self.logger.info(f"Couldn't join: {response.content.message}")

    async def find_successor(self, target_id: int) -> ChordNodeReference:
        if is_between(
            target_id,
            (self.predecessor.node_id + 1) % (1 << self.id_bitlen),
            self.node_id,
        ):
            return self.auto_ref

        if is_between(
            target_id, (self.node_id + 1) % (1 << self.id_bitlen), self.succesor.node_id
        ):
            return self.succesor

        best_match = self.succesor
        for entry in self.finger_table:
            if is_between(target_id, self.node_id, entry.node_id):
                break
            best_match = entry

        response = await self.send_message(
            SUCC_REQUEST,
            SuccRequestMessage(target_id=target_id),
            best_match.ip_address,
            best_match.port,
            best_match.node_id,
        )

        assert response and isinstance(response.content, SuccResponse)

        return ChordNodeReference(
            response.content.ip_address,
            response.content.port,
            response.content.node_id,
        )

    async def find_predecessor(self, target_id: int) -> ChordNodeReference:
        successor = await self.find_successor(target_id)

        response = await self.send_message(
            PRED_REQUEST,
            PredRequestMessage(target_id=target_id),
            successor.ip_address,
            successor.port,
            successor.node_id,
        )

        assert response and isinstance(response.content, PredResponse)

        return ChordNodeReference(
            response.content.ip_address,
            response.content.port,
            response.content.node_id,
        )

    async def request_update_successor(
        self, target: ChordNodeReference, new_successor: ChordNodeReference
    ) -> None:
        if self.node_id == target.node_id:
            self.succesor = new_successor
            return

        await self.send_message(
            UPDATE_SUCC_REQUEST,
            UpdateSuccRequestMessage(
                new_succ_ip_address=new_successor.ip_address,
                new_succ_port=new_successor.port,
                new_succ_node_id=new_successor.node_id,
            ),
            target.ip_address,
            target.port,
            target.node_id,
        )

    async def request_update_predecessor(
        self, target: ChordNodeReference, new_predecessor: ChordNodeReference
    ) -> None:
        if self.node_id == target.node_id:
            self.predecessor = new_predecessor
            return

        await self.send_message(
            UPDATE_PRED_REQUEST,
            UpdatePredRequestMessage(
                new_pred_ip_address=new_predecessor.ip_address,
                new_pred_port=new_predecessor.port,
                new_pred_node_id=new_predecessor.node_id,
            ),
            target.ip_address,
            target.port,
            target.node_id,
        )

    async def update_finger_table_static(
        self, from_index: int, to_index: int, new_responsible: ChordNodeReference
    ) -> None:
        for i in range(self.id_bitlen):
            entry_id = (self.node_id + (1 << i)) % (1 << self.id_bitlen)

            if is_between(entry_id, from_index, to_index):
                self.finger_table[i] = new_responsible

    async def update_all_finger_tables(
        self,
        from_index: int | None = None,
        to_index: int | None = None,
        new_responsible: ChordNodeReference | None = None,
    ) -> None:
        if new_responsible is None or from_index is None or to_index is None:
            new_responsible = self.auto_ref
            from_index = (self.predecessor.node_id + 1) % (1 << self.id_bitlen)
            to_index = self.node_id

        new_singnature = uuid4().hex

        # This is O(N log N), I DO NOT KNOW HOW TO IMPROVE IT :'(
        last = self.auto_ref
        current = self.succesor

        while current.node_id != self.node_id:
            self.logger.debug(f"Updating ftable of {current.node_id}.")

            await self.update_finger_table_static(
                (last.node_id + 1) % (1 << self.id_bitlen),
                current.node_id,
                current,
            )

            response = await self.send_message(
                UPDATE_FTABLE_REQUEST,
                UpdateFTableRequest(
                    from_index=from_index,
                    to_index=to_index,
                    new_responsible_ip_address=new_responsible.ip_address,
                    new_responsible_port=new_responsible.port,
                    new_responsible_node_id=new_responsible.node_id,
                    new_signature=new_singnature,
                ),
                current.ip_address,
                current.port,
                current.node_id,
            )

            assert response and isinstance(response.content, SuccResponse)

            last = current

            current = ChordNodeReference(
                response.content.ip_address,
                response.content.port,
                response.content.node_id,
            )

        await self.update_finger_table_static(
            (self.predecessor.node_id + 1) % (1 << self.id_bitlen),
            self.node_id,
            self.auto_ref,
        )

        self.ring_signature = new_singnature

    async def ping_node(
        self, node: ChordNodeReference
    ) -> tuple[ChordNodeReference, ChordNodeReference] | None:
        try:
            response = await asyncio.wait_for(
                self.send_message(
                    PING,
                    MessageContent(),
                    node.ip_address,
                    node.port,
                    node.node_id,
                ),
                1.0,
            )

            if response and isinstance(response.content, PingResponse):
                succesor = ChordNodeReference(
                    response.content.succ_ip_address,
                    response.content.succ_port,
                    response.content.succ_node_id,
                )

                predecessor = ChordNodeReference(
                    response.content.pred_ip_address,
                    response.content.pred_port,
                    response.content.pred_node_id,
                )

                return predecessor, succesor
        except Exception:
            return None

        return None

    async def get_replicants(
        self, k: int, start: ChordNodeReference | None = None
    ) -> List[ChordNodeReference]:
        start = self.auto_ref if not start else start
        current = start
        replicants: List[ChordNodeReference] = [start]

        for _ in range(k - 1):
            succ = await self.find_successor(
                (current.node_id + 1) % (1 << self.id_bitlen)
            )

            if succ.node_id == start.node_id:
                break

            replicants.append(succ)
            current = succ

        return replicants

    async def start_discovery_server(
        self,
        multicast_group: str = "224.0.0.1",
        port: int = MULTICAST_PORT,
    ):
        class DiscoveryServerProtocol(asyncio.DatagramProtocol):
            def __init__(_self):
                _self.transport = None

            def connection_made(_self, transport):
                _self.transport = transport
                self.logger.info(f"Discovery server ready on {self.ip_address}:{port}.")

            def datagram_received(_self, data: bytes, addr: str) -> None:
                rcv_message = ChordMessage.decode(data)

                if not rcv_message:
                    self.logger.debug(
                        f"Invalid multicast message received: {data.decode()}"
                    )
                    return

                if rcv_message.ring_signature.strip():
                    self.logger.debug(
                        f"Invalid ring signature received on multicast: {rcv_message.ring_signature}"
                    )
                    return

                ip_addres, _ = addr
                port = self.port

                node_ref = ChordNodeReference(
                    ip_addres,
                    port,
                    rcv_message.source_id,
                )

                time.sleep(0.2)

                asyncio.create_task(self.join_node(node_ref))

            def error_received(_self, exc: Exception) -> None:
                self.logger.error(f"Multicast error received: {exc}")

            def connection_lost(_self, exc: Exception) -> None:
                self.logger.error(f"Multicast connection lost: {exc}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", port))

        group = socket.inet_aton(multicast_group)
        mreq = struct.pack("4sL", group, socket.INADDR_ANY)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        loop = asyncio.get_running_loop()

        await loop.create_datagram_endpoint(
            lambda: DiscoveryServerProtocol(),
            sock=sock,
        )

        while True:
            await asyncio.sleep(100000)

    async def join_node(self, node_ref: ChordNodeReference) -> None:
        succ = await self.find_successor(node_ref.node_id)
        pred = await self.find_predecessor(succ.node_id)

        if succ.node_id == node_ref.node_id:
            # The node already is joined to the ring
            return

        self.logger.debug("Adopting node")
        adopt_response = await self.send_message(
            ADOPTION_REQUEST,
            MessageContent(),
            node_ref.ip_address,
            node_ref.port,
            node_ref.node_id,
        )

        if (
            not adopt_response
            or not isinstance(adopt_response.content, GenericResponse)
            or not adopt_response.content.is_success
        ):
            # The node cannot be adopted
            self.logger.debug("Cannot adopt node")

            return

        self.logger.debug("Node adopted")

        await self.request_update_successor(node_ref, succ)
        await self.request_update_predecessor(node_ref, pred)

        await self.request_update_successor(pred, node_ref)
        await self.request_update_predecessor(succ, node_ref)

    def multicast_sender(
        self,
        message_content: BaseModel,
        multicast_group: str = "224.0.0.1",
        port: int = MULTICAST_PORT,
    ) -> None:
        message = ChordMessage(
            MULTICAST,
            self.node_id,
            "",
            message_content,
        )

        message_encoded = message.encode()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        ttl = struct.pack("b", 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        try:
            sock.sendto(message_encoded, (multicast_group, port))
            self.logger.debug("Message sent using multicast.")
        except Exception as ex:
            self.logger.debug(f"Error sending multicast message: {ex}")
        finally:
            sock.close()

    async def discover(self):
        if self.succesor.node_id != self.predecessor.node_id:
            self.logger.warning("This node already is connected to a network.")
            return

        self.multicast_sender(MessageContent())

        await asyncio.sleep(1)

        await self.update_all_finger_tables()

        if self.succesor.node_id != self.node_id:
            self.logger.info("Successfully joined the network.")
        else:
            self.logger.info("No network available, starting a new one.")

    async def discover_join_start(self) -> None:
        await asyncio.gather(
            self.discover(),
            self.start(),
        )

    @classmethod
    def get_instance(cls):
        return cls._instance

    async def check_file(self, file_id: str, target: ChordNodeReference) -> bool:
        response = await self.send_message(
            CHECK_FILE,
            CheckFileRequest(file_id=file_id),
            target.ip_address,
            target.port,
            target.node_id,
        )

        if (
            not response
            or not isinstance(response.content, GenericResponse)
            or not response.content.is_success
        ):
            return False
        return True

    async def send_file(self, file_id: str, target: ChordNodeReference) -> None:
        filename = f"{self.file_path}/{file_id}"
        file_size = os.path.getsize(filename)

        reader, writer, _ = await self.get_sending_stream(
            target.ip_address, target.port
        )

        response = await self.send_message(
            FILE_SEND_REQUEST,
            SendFileRequest(file_id=file_id, file_size=file_size),
            reader=reader,
            writer=writer,
            target_id=target.node_id,
            force_get_response=True,
        )

        if (
            not response
            or not isinstance(response.content, GenericResponse)
            or not response.content.is_success
        ):
            return

        try:
            with open(filename, "rb") as file:
                while True:
                    chunk = file.read(1024)

                    if not chunk:
                        break

                    writer.write(chunk)

                await writer.drain()

                self.logger.info(
                    f"File {file_id} sent successfully to {target.node_id}."
                )
        except Exception as e:
            self.logger.error(f"Failed to send file {file_id}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def receive_file(
        self,
        file_id: str,
        file_size: int,
        writer: asyncio.StreamWriter,
        reader: asyncio.StreamReader,
    ) -> None:
        filename = f"{self.file_path}/{file_id}"

        try:
            with open(filename, "wb") as file:
                while file_size > 0:
                    chunk = await reader.read(1024)

                    if not chunk:
                        break

                    file.write(chunk)
                    file_size -= len(chunk)

                self.logger.info(f"File {file_id} received successfully.")

            if os.path.getsize(filename) < file_size:
                self.logger.error(f"File {file_id} is corrupted and will be removed.")
                os.remove(filename)

        except Exception as e:
            self.logger.error(f"Failed to receive file {file_id}: {e}")


def get_hash(key: str, bit_count: int = 32) -> int:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(key.encode("utf-8"))
    hash_hex = sha256_hash.hexdigest()
    hash_int = int(hash_hex, 16)

    return hash_int % (1 << bit_count)


def hash_string(key: str) -> str:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(key.encode("utf-8"))
    hash_hex = sha256_hash.hexdigest()

    return hash_hex


def get_ip_address(ifname: str = "eth0") -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip_address = fcntl.ioctl(  # type: ignore
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack("256s", ifname[:15].encode("utf-8")),
        )[20:24]
        return socket.inet_ntoa(ip_address)
    except Exception:
        return "127.0.0.1"


def is_between(id: int, a: int, b: int) -> bool:
    if a <= b:
        return a <= id and id <= b
    return a <= id or id <= b


async def main() -> None:
    ip = get_ip_address()
    port = 5000
    id = get_hash(f"{ip}:{port}")

    node = ChordNode(ip, port, id, is_debug=True)

    print(f"Node with Id {id} on {ip}:{port}.")
    choice = input("1 to start node as a new network\n2 to search and join a network\n")

    if choice == "1":
        await node.start()
    elif choice == "2":
        await node.discover_join_start()
        # await node.request_join("10.0.1.2", 5000, 4206084663)
        # await node.start()
    else:
        print("Invalid option!!!")


if __name__ == "__main__":
    asyncio.run(main())
