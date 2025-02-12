# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

import numpy as np

import cirq


class OtherX(cirq.testing.SingleQubitGate):
    def _unitary_(self) -> np.ndarray:
        return np.array([[0, 1], [1, 0]])


class NoUnitary(cirq.testing.SingleQubitGate):
    pass


class OtherCNOT(cirq.testing.TwoQubitGate):
    def _unitary_(self) -> np.ndarray:
        return np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])


def test_convert_to_ion_gates():
    q0 = cirq.GridQubit(0, 0)
    q1 = cirq.GridQubit(0, 1)
    op = cirq.CNOT(q0, q1)
    circuit = cirq.Circuit()
    ion_gateset = cirq.ion.ion_device._IonTargetGateset()
    with cirq.testing.assert_deprecated(
        "cirq_aqt.aqt_device.AQTTargetGateset", deadline='v0.16', count=None
    ):
        convert_to_ion_gates = cirq.ion.ConvertToIonGates()

    with pytest.raises(TypeError):
        convert_to_ion_gates.convert_one(circuit)

    no_unitary_op = NoUnitary().on(q0)
    with pytest.raises(TypeError):
        convert_to_ion_gates.convert_one(no_unitary_op)
    assert ion_gateset._decompose_single_qubit_operation(no_unitary_op, 0) is NotImplemented

    with cirq.testing.assert_deprecated(
        "cirq_aqt.aqt_device.AQTTargetGateset", deadline='v0.16', count=None
    ):
        assert cirq.ion.ConvertToIonGates(ignore_failures=True).convert_one(no_unitary_op) == [
            no_unitary_op
        ]
    rx = convert_to_ion_gates.convert_one(OtherX().on(q0))
    rx_via_gateset = ion_gateset._decompose_single_qubit_operation(OtherX().on(q0), 0)
    assert cirq.approx_eq(rx, [cirq.PhasedXPowGate(phase_exponent=1.0).on(cirq.GridQubit(0, 0))])
    assert cirq.approx_eq(
        rx_via_gateset, [cirq.PhasedXPowGate(phase_exponent=1.0).on(cirq.GridQubit(0, 0))]
    )

    rop = convert_to_ion_gates.convert_one(op)
    rop_via_gateset = ion_gateset._decompose_two_qubit_operation(op, 0)
    cirq.testing.assert_circuits_with_terminal_measurements_are_equivalent(
        cirq.Circuit(rop), cirq.Circuit(rop_via_gateset), atol=1e-6
    )
    assert cirq.approx_eq(
        rop,
        [
            cirq.ry(np.pi / 2).on(op.qubits[0]),
            cirq.ms(np.pi / 4).on(op.qubits[0], op.qubits[1]),
            cirq.rx(-1 * np.pi / 2).on(op.qubits[0]),
            cirq.rx(-1 * np.pi / 2).on(op.qubits[1]),
            cirq.ry(-1 * np.pi / 2).on(op.qubits[0]),
        ],
    )

    rcnot = convert_to_ion_gates.convert_one(OtherCNOT().on(q0, q1))
    assert cirq.approx_eq(
        [op for op in rcnot if len(op.qubits) > 1],
        [cirq.ms(-0.5 * np.pi / 2).on(q0, q1)],
        atol=1e-4,
    )
    assert cirq.allclose_up_to_global_phase(
        cirq.unitary(cirq.Circuit(rcnot)), cirq.unitary(OtherCNOT().on(q0, q1)), atol=1e-7
    )


def test_convert_to_ion_circuit():
    q0 = cirq.LineQubit(0)
    q1 = cirq.LineQubit(1)
    us = cirq.Duration(nanos=1000)
    with cirq.testing.assert_deprecated("cirq_aqt.aqt_device.AQTDevice", deadline='v0.16'):
        ion_device = cirq.IonDevice(us, us, us, [q0, q1])
    with cirq.testing.assert_deprecated(
        "cirq_aqt.aqt_device.AQTTargetGateset", deadline='v0.16', count=None
    ):
        convert_to_ion_gates = cirq.ion.ConvertToIonGates()

    clifford_circuit_1 = cirq.Circuit()
    clifford_circuit_1.append([cirq.X(q0), cirq.H(q1), cirq.ms(np.pi / 4).on(q0, q1)])
    ion_circuit_1 = convert_to_ion_gates.convert_circuit(clifford_circuit_1)
    ion_circuit_1_using_device = ion_device.decompose_circuit(clifford_circuit_1)

    ion_device.validate_circuit(ion_circuit_1)
    ion_device.validate_circuit(ion_circuit_1_using_device)
    cirq.testing.assert_circuits_with_terminal_measurements_are_equivalent(
        clifford_circuit_1, ion_circuit_1, atol=1e-6
    )
    cirq.testing.assert_circuits_with_terminal_measurements_are_equivalent(
        clifford_circuit_1, ion_circuit_1_using_device, atol=1e-6
    )

    clifford_circuit_2 = cirq.Circuit()
    clifford_circuit_2.append([cirq.X(q0), cirq.CNOT(q1, q0), cirq.ms(np.pi / 4).on(q0, q1)])
    ion_circuit_2 = convert_to_ion_gates.convert_circuit(clifford_circuit_2)
    ion_circuit_2_using_device = ion_device.decompose_circuit(clifford_circuit_2)
    ion_device.validate_circuit(ion_circuit_2)
    ion_device.validate_circuit(ion_circuit_2_using_device)
    cirq.testing.assert_circuits_with_terminal_measurements_are_equivalent(
        clifford_circuit_2, ion_circuit_2, atol=1e-6
    )
    cirq.testing.assert_circuits_with_terminal_measurements_are_equivalent(
        clifford_circuit_2, ion_circuit_2_using_device, atol=1e-6
    )
