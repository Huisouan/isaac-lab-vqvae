"""
  Generated by Eclipse Cyclone DDS idlc Python Backend
  Cyclone DDS IDL version: v0.11.0
  Module: unitree_hg.msg.dds_
  IDL file: MainBoardState_.idl

"""

from enum import auto
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass

import cyclonedds.idl as idl
import cyclonedds.idl.annotations as annotate
import cyclonedds.idl.types as types

# root module import for resolving types
# import unitree_hg


@dataclass
@annotate.final
@annotate.autoid("sequential")
class MainBoardState_(idl.IdlStruct, typename="unitree_hg.msg.dds_.MainBoardState_"):
    fan_state: types.array[types.uint16, 6]
    temperature: types.array[types.int16, 6]
    value: types.array[types.float32, 6]
    state: types.array[types.uint32, 6]

