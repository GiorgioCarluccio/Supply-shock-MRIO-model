"""Modelling layer: SAM-to-model transformation and supply-shock propagation.

Public surface:

* :func:`label_parser.parse_account_label`, :func:`label_parser.classify_account`
* :func:`input_builder.build_model_inputs`, :func:`input_builder.load_model_inputs`
* :class:`io_model.IOClimateModel`
* :func:`propagation.propagate_once`
* :mod:`kpi`, :func:`results.summarize_run`
"""

from __future__ import annotations

from . import input_builder, io_model, kpi, label_parser, propagation, results
from .io_model import IOClimateModel
from .propagation import propagate_once
from .results import ModelResults, summarize_run

__all__ = [
    "input_builder",
    "io_model",
    "kpi",
    "label_parser",
    "propagation",
    "results",
    "IOClimateModel",
    "propagate_once",
    "ModelResults",
    "summarize_run",
]
