"""
  Generated by Eclipse Cyclone DDS idlc Python Backend
  Cyclone DDS IDL version: v0.11.0
  Module: unitree_hg.msg.dds_
  IDL file: BmsState_.idl

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
class BmsState_(idl.IdlStruct, typename="unitree_hg.msg.dds_.BmsState_"):
    version_high: types.uint8
    version_low: types.uint8
    fn: types.uint8
    cell_vol: types.array[types.uint16, 40]
    bmsvoltage: types.array[types.uint32, 3]
    current: types.int32
    soc: types.uint8
    soh: types.uint8
    temperature: types.array[types.int16, 12]
    cycle: types.uint16
    manufacturer_date: types.uint16
    bmsstate: types.array[types.uint32, 5]
    reserve: types.array[types.uint32, 3]

