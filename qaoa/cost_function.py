"""
Implementation of the QAOA cost_functions. We inherit from vqe/cost_functions
and change only the QAOA specific details.

TODO
----
Change type of `reg` to Iterable or create custom type for it.
"""


from typing import Union, List, Type

from pyquil import Program
from pyquil.quil import MemoryReference
from pyquil.gates import RX, RZ, CPHASE, H
from pyquil.paulis import PauliSum
from pyquil.api._wavefunction_simulator import WavefunctionSimulator
from pyquil.api._quantum_computer import QuantumComputer

from vqe.cost_function import PrepareAndMeasureOnQVM, PrepareAndMeasureOnWFSim
from qaoa.parameters import AbstractQAOAParameters, GeneralQAOAParameters

def _qaoa_mixing_ham_rotation(betas: MemoryReference,
                              reg: Union[List, range]) -> Program:
    """Produce parametric Quil-Code for the mixing hamiltonian rotation.

    Parameters
    ----------
    betas : MemoryReference
        Classic register to read the betas from.
    reg : Union[List, Range]
        The register to apply the X-rotations on.

    Returns
    -------
    Program
        Parametric Quil Program containing the X-Rotations.

    """
    if len(reg) != betas.declared_size:
        raise ValueError("betas must have the same length as reg")

    p = Program()
    for i, qubit in enumerate(reg):
        p.inst(RX(-2 * betas[i], qubit))
    return p


def _qaoa_cost_ham_rotation(gammas_pairs: MemoryReference,
                            qubit_pairs: List,
                            gammas_singles: MemoryReference,
                            qubit_singles: List) -> Program:
    """Produce the Quil-Code for the cost-hamiltonian rotation.

    Parameters
    ----------
    gammas_pairs : MemoryReference
        Classic register to read the gammas_pairs from.
    qubit_pairs : List
        List of the Qubit pairs to apply rotations on.
    gammas_singles : MemoryReference
        Classic register to read the gammas_singles from.
    qubit_singles : List
        List of the single qubits to apply rotations on.

    Returns
    -------
    Program
        Parametric Quil code containing the Z-Rotations.

    """
    p = Program()

    if len(qubit_pairs) != gammas_pairs.declared_size:
        raise ValueError("gammas_pairs must have the same length as qubits_pairs")

    for i, qubit_pair in enumerate(qubit_pairs):
        p.inst(RZ(2 * gammas_pairs[i], qubit_pair[0]))
        p.inst(RZ(2 * gammas_pairs[i], qubit_pair[1]))
        p.inst(CPHASE(-4 * gammas_pairs[i], qubit_pair[0], qubit_pair[1]))

    if gammas_singles.declared_size != len(qubit_singles):
        raise ValueError("gammas_singles must have the same length as qubit_singles")

    for i, qubit in enumerate(qubit_singles):
        p.inst(RZ(2 * gammas_singles[i], qubit))

    return p


# TODO check, whether aliased angles are supported yet
def _qaoa_annealing_program(qaoa_params: Type[AbstractQAOAParameters]) -> Program:
    """Create parametric quil code for QAOA annealing circuit.

    Parameters
    ----------
    qaoa_params : Type[AbstractQAOAParameters]
        The parameters of the QAOA circuit.

    Returns
    -------
    Program
        Parametetric Quil Program with the annealing circuit.

    """
    (reg, qubits_singles, qubits_pairs, timesteps) =\
        (qaoa_params.reg, qaoa_params.qubits_singles,
         qaoa_params.qubits_pairs, qaoa_params.timesteps)

    p = Program()
    # create list of memory references to store angles in.
    # Has to be so nasty, because aliased memories are not supported yet...
    betas = []
    gammas_singles = []
    gammas_pairs = []
    for i in range(timesteps):
        beta = p.declare('betas{}'.format(i),
                         memory_type='REAL',
                         memory_size=len(reg))
        gamma_singles = p.declare('gammas_singles{}'.format(i),
                                  memory_type='REAL',
                                  memory_size=len(qubits_singles))
        gamma_pairs = p.declare('gammas_pairs{}'.format(i),
                                memory_type='REAL',
                                memory_size=len(qubits_pairs))
        betas.append(beta)
        gammas_singles.append(gamma_singles)
        gammas_pairs.append(gamma_pairs)

    # apply cost and mixing hamiltonian alternating
    for i in range(timesteps):
        p += _qaoa_cost_ham_rotation(gammas_pairs[i], qubits_pairs,
                                     gammas_singles[i], qubits_singles)
        p += _qaoa_mixing_ham_rotation(betas[i], reg)
    return p


def _prepare_all_plus_state(reg) -> Program:
    """Prepare the |+>...|+> state on all qubits in reg."""
    p = Program()
    for qubit in reg:
        p.inst(H(qubit))
    return p


def prepare_qaoa_ansatz(qaoa_params: Type[AbstractQAOAParameters]) -> Program:
    """Create parametric quil code for QAOA circuit.

    Parameters
    ----------
    qaoa_params : Type[AbstractQAOAParameters]
        The parameters of the QAOA circuit.

    Returns
    -------
    Program
        Parametetric Quil Program with the whole circuit.

    """
    p = _prepare_all_plus_state(qaoa_params.reg)
    p += _qaoa_annealing_program(qaoa_params)
    return p


def make_qaoa_memory_map(qaoa_params: Type[AbstractQAOAParameters]) -> dict:
    """Make a memory map for the QAOA Ansatz as produced by `prepare_qaoa_ansatz`.

    Parameters
    ----------
    qaoa_params : Type(AbstractQAOAParameters)
        QAOA parameters to take angles from

    Returns
    -------
    dict:
        A memory_map as expected by QVM.run().

    """
    memory_map = {}
    for i in range(qaoa_params.timesteps):
        memory_map['betas{}'.format(i)] = qaoa_params.betas[i]
        memory_map['gammas_singles{}'.format(i)] = qaoa_params.gammas_singles[i]
        memory_map['gammas_pairs{}'.format(i)] = qaoa_params.gammas_pairs[i]
    return memory_map


class QAOACostFunctionOnWFSim(PrepareAndMeasureOnWFSim):
    """
    A cost function that inherits from PrepareAndMeasureOnWFSim and implements
    the specifics of QAOA
    """

    def __init__(self,
                 hamiltonian: PauliSum,
                 params: Type[AbstractQAOAParameters],
                 sim: WavefunctionSimulator,
                 return_standard_deviation=False,
                 noisy=False,
                 log=None):
        """Create a cost-function for QAOA.

        Parameters
        ----------
        hamiltonian : PauliSum
            The cost hamiltonian
        params : Type[AbstractQAOAParameters]
            Form of the QAOA parameters (with timesteps and type fixed for this instance)
        sim : WavefunctionSimulator
            connection to the WavefunctionSimulator to run the simulation on
        return_standard_deviation : bool
            return standard deviation or only expectation value?
        noisy : False
            Add simulated samplign noise?
        log : list
            List to keep log of function calls
        """
        self.params = params
        super().__init__(prepare_qaoa_ansatz(params),
                         make_memory_map=make_qaoa_memory_map,
                         hamiltonian=hamiltonian,
                         sim=sim,
                         return_standard_deviation=return_standard_deviation,
                         noisy=noisy,
                         log=log)

    def __call__(self, params, nshots: int=1000):
        self.params.update(params)
        out = super().__call__(self.params, nshots=nshots)
        return out

class QAOACostFunctionOnQVM(PrepareAndMeasureOnQVM):
    """
    A cost function that inherits from PrepareAndMeasureOnQVM and implements
    the specifics of QAOA
    """

    def __init__(self,
                 hamiltonian: PauliSum,
                 params: Type[AbstractQAOAParameters],
                 qvm: QuantumComputer,
                 return_standard_deviation=False,
                 base_numshots: int = 100,
                 log=None):
        """Create a cost-function for QAOA.

        Parameters
        ----------
        hamiltonian : PauliSum
            The cost hamiltonian
        params : Type[AbstractQAOAParameters]
            Form of the QAOA parameters (with timesteps and type fixed for this instance)
        qvm : QuantumComputer
            connection to the QuantumComputer to run on
        return_standard_deviation : bool
            return standard deviation or only expectation value?
        param base_numshots : int
            numshots to compile into the binary. The argument nshots of __call__
            is then a multplier of this.
        log : list
            List to keep log of function calls
        """
        self.params = params
        super().__init__(prepare_qaoa_ansatz(params),
                         make_memory_map=make_qaoa_memory_map,
                         hamiltonian=hamiltonian,
                         qvm=qvm,
                         return_standard_deviation=return_standard_deviation,
                         base_numshots = base_numshots,
                         log=log)

    def __call__(self, params, nshots: int=10):
        self.params.update(params)
        out = super().__call__(self.params, nshots=nshots)
        return out