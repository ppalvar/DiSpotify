import asyncio
import fcntl
import hashlib
import pickle
import logging
import socket
import ssl
import struct
from uuid import uuid4
from typing import List, Optional
from pydantic import BaseModel


from chord.chord_messages import (
    GenericResponse,
    JoinRequestMessage,
    JoinResponse,
    MessageContent,
    PingResponse,
    PredRequestMessage,
    PredResponse,
    SuccRequestMessage,
    SuccResponse,
    UpdateFTableRequest,
    UpdatePredRequestMessage,
    UpdateSuccRequestMessage,
)

PING_INTERVAL = 3  # seconds

UPDATE_FTABLE_REQUEST = "UPDATE_FTABLE_REQUEST"
JOIN_REQUEST = "JOIN_REQUEST"
SUCC_REQUEST = "SUCC_REQUEST"
PRED_REQUEST = "PRED_REQUEST"
UPDATE_PRED_REQUEST = "UPDATE_PRED_REQUEST"
UPDATE_SUCC_REQUEST = "UPDATE_SUCC_REQUEST"
RESPONSE = "RESPONSE"
PING = "PING"

CHORD_MESSAGE_TYPES = [
    JOIN_REQUEST,
    RESPONSE,
    SUCC_REQUEST,
    UPDATE_FTABLE_REQUEST,
    PRED_REQUEST,
    UPDATE_PRED_REQUEST,
    UPDATE_SUCC_REQUEST,
    PING,
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
        ip_address: str | None = "localhost",
        port: int | None = 4321,
        node_id: int | None = 0,
        id_bitlen: int = 32,
        is_debug: bool = False,
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

            self.is_debug = is_debug

            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)

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
            self.is_debug and self.logger.info(
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
                self.is_debug and self.logger.debug(
                    f"Received message from node {message.source_id}."
                )
                await self.handle_message(message, reader, writer)
            else:
                self.is_debug and self.logger.debug("Received invalid message")
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            self.is_debug and self.logger.debug(
                f"Some error occured while handling message: {e}"
            )

        print(self.finger_table)

    async def stabilize(self) -> None:
        last_entry = self.succesor

        while True:
            await asyncio.sleep(PING_INTERVAL)

            if self.succesor.node_id != self.node_id:
                succ_response = await self.ping_node(self.succesor)

                if not succ_response:
                    self.is_debug and self.logger.debug(
                        "Successor node died, stibilizing..."
                    )

                    self.succesor = last_entry

                    await self.request_update_predecessor(last_entry, self.auto_ref)

                    await self.update_all_finger_tables(
                        self.node_id + 1,
                        self.succesor.node_id,
                        self.succesor,
                    )

                    self.is_debug and self.logger.debug("STABILIZING DONE!")

                else:
                    _, last_entry = succ_response
                    self.is_debug and self.logger.debug("Everything all right!")

    async def start(self) -> None:
        await asyncio.gather(self.listen(), self.stabilize())

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
                    "RESPONSE",
                    GenericResponse(is_success=False, message="Your Id is not valid."),
                    reader=reader,
                    writer=writer,
                )

            succesor = await self.find_successor(message.content.my_id)

            if succesor.node_id == message.content.my_id:
                await self.send_message(
                    "RESPONSE",
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
                "RESPONSE",
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

        elif self.ring_signature != message.ring_signature:
            await self.send_message(
                "RESPONSE",
                GenericResponse(
                    is_success=False,
                    message="The provided signature is not valid.",
                ),
                reader=reader,
                writer=writer,
                omit_signature=True,
            )

        if ms_type == SUCC_REQUEST:
            assert isinstance(message.content, SuccRequestMessage)
            succesor = await self.find_successor(message.content.target_id)

            self.is_debug and self.logger.debug(
                f"SUCC REQUEST: {message.source_id} requested succ of {message.content.target_id}, response is {succesor.node_id}."
            )
            success = True

            if not isinstance(message.content, SuccRequestMessage):
                success = False

            await self.send_message(
                "RESPONSE",
                SuccResponse(
                    is_success=success,
                    ip_address=succesor.ip_address,
                    port=succesor.port,
                    node_id=succesor.node_id,
                ),
                reader=reader,
                writer=writer,
            )

        if ms_type == PRED_REQUEST:
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

        if ms_type == UPDATE_FTABLE_REQUEST:
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
                "RESPONSE",
                SuccResponse(
                    is_success=True,
                    ip_address=self.succesor.ip_address,
                    port=self.succesor.port,
                    node_id=self.succesor.node_id,
                ),
                reader=reader,
                writer=writer,
            )

        if ms_type == UPDATE_SUCC_REQUEST:
            assert isinstance(message.content, UpdateSuccRequestMessage)

            self.succesor = ChordNodeReference(
                message.content.new_succ_ip_address,
                message.content.new_succ_port,
                message.content.new_succ_node_id,
            )

        if ms_type == UPDATE_PRED_REQUEST:
            assert isinstance(message.content, UpdatePredRequestMessage)

            self.predecessor = ChordNodeReference(
                message.content.new_pred_ip_address,
                message.content.new_pred_port,
                message.content.new_pred_node_id,
            )

        if ms_type == PING:
            await self.send_message(
                "RESPONSE",
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
            if not reader or not writer:
                ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                ssl_context.load_verify_locations(cafile="ssl_cert/cert.pem")
                reader, writer = await asyncio.open_connection(
                    target_ip, target_port, ssl=ssl_context
                )
                clean = True

            writer.write(message_encoded)
            await writer.drain()

            self.is_debug and self.logger.debug(f"Message sent to node {target_id}.")

            if clean:
                response = await reader.read(1024)
                writer.close()
                await writer.wait_closed()

                response = ChordMessage.decode(response)
                return response
        except Exception as e:
            self.is_debug and self.logger.debug(f"Failed to send message: {e}")

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

            self.is_debug and self.logger.debug("Successfully joined!")
        else:
            self.is_debug and self.logger.debug(
                f"Couldn't join: {response.content.message}"
            )

    async def find_successor(self, target_id: int) -> ChordNodeReference:
        if is_between(target_id, self.predecessor.node_id + 1, self.node_id):
            self.is_debug and self.logger.debug(
                f"({self.node_id}, {self.predecessor.node_id}, {self.succesor.node_id})Succ of {target_id} is current node {self.node_id}"
            )
            return self.auto_ref

        if is_between(target_id, self.node_id + 1, self.succesor.node_id):
            self.is_debug and self.logger.debug(
                f"({self.node_id}, {self.predecessor.node_id}, {self.succesor.node_id})Succ of {target_id} is successor of current node {self.succesor.node_id}"
            )
            return self.succesor

        best_match = self.succesor
        for entry in self.finger_table:
            if is_between(target_id, self.node_id, entry.node_id):
                best_match = entry

        self.is_debug and self.logger.debug(
            f"({self.node_id}, {self.predecessor.node_id}, {self.succesor.node_id})Succ of {target_id} is in {best_match.node_id}"
        )

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
            from_index = self.predecessor.node_id + 1
            to_index = self.node_id

        new_singnature = uuid4().hex

        # This is O(N log N), I DO NOT KNOW HOW TO IMPROVE IT :'(
        last = self.auto_ref
        current = self.succesor

        while current.node_id != self.node_id:
            await self.update_finger_table_static(
                last.node_id + 1,
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
            self.predecessor.node_id + 1,
            self.node_id,
            self.auto_ref,
        )

        self.ring_signature = new_singnature

    async def ping_node(
        self, node: ChordNodeReference
    ) -> tuple[ChordNodeReference, ChordNodeReference] | None:
        try:
            response = await self.send_message(
                PING,
                MessageContent(),
                node.ip_address,
                node.port,
                node.node_id,
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

    async def get_replicants(self, k: int) -> List[ChordNodeReference]:
        replicants: List[ChordNodeReference] = []

        current = self.auto_ref
        for _ in range(k):
            succ = await self.find_successor(current.node_id + 1)
            replicants.append(succ)
            current = succ

        return replicants


def get_hash(key: str, bit_count: int = 32) -> int:
    sha256_hash = hashlib.sha256()
    sha256_hash.update(key.encode("utf-8"))
    hash_hex = sha256_hash.hexdigest()
    hash_int = int(hash_hex, 16)

    return hash_int % (2 << bit_count)


def get_ip_address(ifname: str = "eth0") -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip_address = fcntl.ioctl(
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
    id = int(input("Enter the id: "))
    ip = "localhost"
    port = 5000 + id

    node = ChordNode(ip, port, id, 10, True)

    if port != 5000:
        await node.request_join(ip, 5000, 0)

    await node.start()


if __name__ == "__main__":
    asyncio.run(main())
