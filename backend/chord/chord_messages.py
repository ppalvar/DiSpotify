from typing import Optional
from pydantic import BaseModel


class JoinRequestMessage(BaseModel):
    my_ip_address: str
    my_port: int
    my_id: int
    my_id_bitlen: int


class SuccRequestMessage(BaseModel):
    target_id: int


class PredRequestMessage(SuccRequestMessage):
    pass


class UpdateSuccRequestMessage(BaseModel):
    new_succ_ip_address: str
    new_succ_port: int
    new_succ_node_id: int


class UpdatePredRequestMessage(BaseModel):
    new_pred_ip_address: str
    new_pred_port: int
    new_pred_node_id: int


class UpdateFTableRequest(BaseModel):
    from_index: int
    to_index: int

    new_responsible_ip_address: str
    new_responsible_port: int
    new_responsible_node_id: int

    new_signature: str


class GenericResponse(BaseModel):
    is_success: bool
    message: Optional[str] = None


class SuccResponse(GenericResponse):
    ip_address: str
    port: int
    node_id: int


class PredResponse(SuccResponse):
    pass


class JoinResponse(GenericResponse):
    succ_ip_address: str
    succ_port: int
    succ_node_id: int
    pred_ip_address: str
    pred_port: int
    pred_node_id: int


class PingResponse(JoinResponse):
    pass


class MessageContent(BaseModel):
    text: str = "-"
