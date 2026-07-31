# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

"""
Pore Networks
-------------

Data structures describing a pore network model and its time-resolved state
variables, typically imported from a MATLAB ``.mat`` file:

* :class:`PoreNetwork` -- network geometry and its ordered list of states.
* :class:`PoreNetworkState` -- one state of the network and its quantities.
* :class:`PoreNetworkQuantity` -- per-pore and per-throat values of one quantity.
* :class:`StateVariableMap` -- maps a quantity to the ``.mat`` variables holding it.
"""

from collections.abc import Iterator, Sequence
from math import floor
from pathlib import Path
from typing import Self

import numpy as np
from h5py import File

from porescene.utility import InterpolationType


class PoreNetworkQuantity:
    """
    A wrapper for a single quantity of one state of a pore network.
    """

    def __init__(
        self, n: str, interpolation: InterpolationType = InterpolationType.PREVIOUS
    ) -> None:
        self.name = n
        self.interpolation = interpolation
        self.throat_values = None
        self.pore_values = None

    def set_data(self, vals_p: np.ndarray | None, vals_t: np.ndarray | None) -> Self:
        """
        Sets pore and throat related data at once.
        """
        self.pore_values = vals_p
        self.throat_values = vals_t
        return self

    @property
    def max(self) -> float:
        """
        Hightest value from all values across pores and throats.
        """
        m1 = np.nan
        m2 = np.nan
        if self.pore_values is not None:
            m1 = self.pore_values.max()
        if self.throat_values is not None:
            m2 = self.throat_values.max()
        return np.nanmax([m1, m2])

    @property
    def min(self) -> float:
        """
        Lowest value from all values across pores and throats.
        """
        m1 = np.nan
        m2 = np.nan
        if self.pore_values is not None:
            m1 = self.pore_values.min()
        if self.throat_values is not None:
            m2 = self.throat_values.min()
        return np.nanmin([m1, m2])

    @property
    def interpolation(self) -> InterpolationType:
        """
        How the quantity's values are resolved between two computed states, see
        :class:`~porescene.utility.InterpolationType`.

        Defaults to :attr:`~porescene.utility.InterpolationType.PREVIOUS`, which never
        reports a value the simulation did not compute. Set it to
        :attr:`~porescene.utility.InterpolationType.LINEAR` for quantities that vary
        smoothly in time.
        """
        return self._interpolation

    @interpolation.setter
    def interpolation(self, arg: InterpolationType) -> Self:
        self._interpolation = arg
        return self

    @property
    def name(self) -> str:
        """Name of the quantity."""
        return self._name

    @name.setter
    def name(self, arg: str) -> Self:
        self._name = arg
        return self

    @property
    def pore_values(self) -> np.ndarray | None:
        """Pore related data values."""
        return self._pore_values

    @pore_values.setter
    def pore_values(self, arg: np.ndarray | None) -> Self:
        self._pore_values = arg
        return self

    @property
    def throat_values(self) -> np.ndarray | None:
        """Throat related data values."""
        return self._throat_values

    @throat_values.setter
    def throat_values(self, arg: np.ndarray | None) -> Self:
        self._throat_values = arg
        return self


class PoreNetworkState:
    """
    A wrapper for one state of a pore network.

    Parameters
    ----------
    quantities : Sequence[PoreNetworkQuantity] | None, optional
        Quantities the state starts out with, by default ``None`` (no quantities).
        The sequence is copied, so the new state can be extended without touching the
        one the quantities came from; the :class:`PoreNetworkQuantity` objects
        themselves are shared, not duplicated.
    no : int | None, optional
        Index of the state in the source data, see :attr:`no`.
    time_point : float | None, optional
        Physical time the state describes, see :attr:`time_point`.
    """

    def __init__(
        self,
        quantities: Sequence[PoreNetworkQuantity] | None = None,
        no: int | None = None,
        time_point: float | None = None,
    ) -> None:
        self.quantities = [] if quantities is None else list(quantities)
        self.no = no
        self.time_point = time_point

    def __iter__(self) -> Iterator[PoreNetworkQuantity]:
        return iter(self.quantities)

    def __len__(self) -> int:
        return len(self.quantities)

    def __setitem__(self, _, quant: PoreNetworkQuantity):
        return self.add_quantity(quant)

    def __getitem__(self, idx: str) -> PoreNetworkQuantity:
        return self.get_quantity(idx)

    def add_quantity(self, quant: PoreNetworkQuantity) -> Self:
        """
        Add a :class:`PoreNetworkQuantity`.
        """
        if self.has_quantity(quant.name):
            self.quantities[self._quantity_index(quant.name)] = quant
        else:
            self._quantities.append(quant)
        return self

    def get_quantity(self, name: str) -> PoreNetworkQuantity:
        """
        Returns a :class:`PoreNetworkQuantity` by name.
        """
        return self.quantities[self._quantity_index(name)]

    def has_quantity(self, name: str) -> bool:
        """
        Check if the model has data about quantity `name`.
        """
        for quant in self.quantities:
            if quant.name == name:
                return True
        return False

    def _quantity_index(self, name) -> int:
        if not self.has_quantity(name):
            raise ValueError(f"Could not find a quantity named '{name}'")
        idx = -1
        for i, quant in enumerate(self._quantities):
            if quant.name == name:
                idx = i
        return idx

    @property
    def no(self) -> int | None:
        """
        Index of the state in the source data, e.g. the column of the ``.mat`` variable
        its values were read from, or ``None`` when the state does not stem from an
        indexed source.

        Identifies *which* sample the state is, not *when* it happened -- see
        :attr:`time_point` for the physical time.
        """
        return self._no

    @no.setter
    def no(self, arg: int | None) -> Self:
        self._no = arg
        return self

    @property
    def quantities(self) -> list[PoreNetworkQuantity]:
        """
        The quantities held by the state.
        """
        return self._quantities

    @quantities.setter
    def quantities(self, arg: list[PoreNetworkQuantity]) -> Self:
        self._quantities = arg
        return self

    @property
    def time_point(self) -> float | None:
        """
        Physical time the state describes, or ``None`` when the source data carries no
        time information.

        Computed results are commonly written at irregular intervals, so the spacing
        between the time points of consecutive states need not be constant, and it is
        generally unrelated to the spacing of their :attr:`no` indices. States without a
        time point stay fully usable -- they are then identified by :attr:`no` alone.
        """
        return self._time_point

    @time_point.setter
    def time_point(self, arg: float | None) -> Self:
        self._time_point = arg
        return self


class StateVariableMap:
    """
    Maps a pore network quantity to the ``.mat`` variables holding its data.

    Relates a single quantity (identified by :attr:`name`) to the names of the MATLAB
    variables that store the quantity's per-pore (sphere) and per-throat (cylinder)
    values, telling :meth:`PoreNetwork.from_mat` and
    :meth:`PoreNetwork.load_states_from_mat` which variables to import.
    """

    def __init__(
        self,
        quant_name: str,
        interpolation: InterpolationType = InterpolationType.PREVIOUS,
    ):
        self.name = quant_name
        self.interpolation = interpolation

    @property
    def interpolation(self) -> InterpolationType:
        """
        How the mapped quantity behaves between two computed states, see
        :class:`~porescene.utility.InterpolationType`.

        Copied onto every :class:`PoreNetworkQuantity` imported through this map, where
        :meth:`PoreNetwork.state_at` reads it. Declared here because it follows from the
        physics of the quantity, not from how it is drawn.
        """
        return self._interpolation

    @interpolation.setter
    def interpolation(self, arg: InterpolationType):

        self._interpolation = arg

    @property
    def name(self) -> str:
        """
        Name of the mapped quantity.
        """
        return self._name

    @name.setter
    def name(self, v: str) -> str:

        self._name = v

    @property
    def variable_sphere(self) -> str | None:
        """
        Name of the ``.mat`` variable holding the per-pore (sphere) values, or ``None``.
        """
        if hasattr(self, "_variable_sphere"):
            return self._variable_sphere
        else:
            return None

    @variable_sphere.setter
    def variable_sphere(self, v: str | None):

        self._variable_sphere = v

    @property
    def variable_cylinder(self) -> str | None:
        """
        Name of the ``.mat`` variable holding the per-throat (cylinder) values, or
        ``None``.
        """
        if hasattr(self, "_variable_cylinder"):
            return self._variable_cylinder
        else:
            return None

    @variable_cylinder.setter
    def variable_cylinder(self, v: str | None):

        self._variable_cylinder = v


class PoreNetwork:
    """
    A pore network model made up of pores (spheres) and throats (cylinders).

    Holds the network geometry (pore/throat radii and positions, boundary pores,
    connectivity and coordination numbers) together with an ordered list of
    :class:`PoreNetworkState` instances describing the network's state variables. Use
    :meth:`from_mat` to build an instance from a MATLAB ``.mat`` file.
    """

    def __init__(self) -> None:
        self.states = []
        self.pore_radius = None
        self.throat_radius = None
        self.pore_coordination_number = None
        self.throat_coordination_number = None

    @classmethod
    def from_mat(
        cls,
        pth: Path,
        vars_nwk: dict[str, str],
        vars_state: Sequence[StateVariableMap] = (),
        no_states: Sequence[int] = (),
        *,
        var_time: str | None = None,
        swap_axes: bool = True,
    ) -> Self:
        """
        Creates a :class:`PoreNetwork` instance by importing the pore network data from a
        MATLAB ``.mat`` file.

        .. attention::

            Variable import from ``.mat`` files is only supported for MATLAB files in
            version 7.3 that are based on `HDF5 <https://github.com/HDFGroup/hdf5>`_.
            When saving the MATLAB file, make sure to set the ``-v7.3`` in MATLAB's
            ``save`` function.

            .. code-block:: matlab
                :caption: MATLAB
                :linenos:

                save('myfile.mat', "-v7.3");

        .. attention::

            While the first index in MATLAB arrays is ``1``, Python (and numpy) arrays
            are ``0``-indexed. This importer function automatically converts the MATLAB
            indices into ``0``-based Python indices.

            Note that this applies to following attributes:

            - :attr:`PoreNetwork.pores_left`
            - :attr:`PoreNetwork.pores_right`
            - :attr:`PoreNetwork.pores_front`
            - :attr:`PoreNetwork.pores_back`
            - :attr:`PoreNetwork.pores_bottom`
            - :attr:`PoreNetwork.pores_top`
            - :attr:`PoreNetwork.throat_neighboring_pores`
            - :attr:`PoreNetwork.pore_neighboring_pores`

        .. attention::

            MATLAB stores multi-dimensional arrays in column-major order, while numpy
            defaults to row-major order. Dumping a voxel image out of MATLAB and reading
            it back with numpy (e.g. via :func:`numpy.fromfile` followed by
            :meth:`~numpy.ndarray.reshape`) therefore reverses the storage order of its
            dimensions, which swaps the array's first and third (spatial) axes while
            leaving the second axis untouched -- what MATLAB calls its first dimension
            ends up as numpy's third axis, and vice versa, while the second dimension
            stays in place.

            Since :func:`porescene.utility.volume2mesh` builds its mesh directly from such
            a numpy voxel array, meshes it produces have their first and third axes
            swapped relative to the coordinate frame the ``.mat`` file's own variables
            (e.g. ``pos_p``) were written in. By default (``swap_axes=True``), this
            importer swaps the first and third columns of every imported position array
            (:attr:`PoreNetwork.pore_position` and its ``_top``/``_bottom``/``_left``/
            ``_right``/``_front``/``_back`` variants) to match, so pore/throat
            coordinates line up with meshes built by
            :func:`~porescene.utility.volume2mesh`. Pass ``swap_axes=False`` to import
            the coordinates verbatim in the MATLAB axis order instead, e.g. when no
            voxel-image mesh is involved.

        Parameters
        ----------
        pth : Path
            Path to the MATLAB ``.mat`` file.
        vars_nwk : dict[str, str]
            A map that specifies the corresponding variables in the ``.mat`` file for the
            attributes of the :class:`PoreNetwork` instance.
        vars_state : Sequence[StateVariableMap], optional
            The :class:`StateVariableMap` instances that relate the state variables in
            the ``.mat`` file to :class:`PoreNetworkQuantity` instances.

            Each :class:`StateVariableMap` carries a quantity name
            (:attr:`StateVariableMap.name`, identical to
            :attr:`PoreNetworkQuantity.name`) together with the names of the ``.mat``
            variables holding the per-pore and per-throat data
            (:attr:`StateVariableMap.variable_sphere` and
            :attr:`StateVariableMap.variable_cylinder`, respectively). A variable left as
            ``None`` is skipped, so a quantity may provide pore data, throat data, or
            both.

            As example: in case of ``"temperature"`` field data, the ``.mat`` file
            contains a variable ``T_pores`` that holds the temperature of each pore,
            while the variable ``T_throats`` holds the temperature values of each throat.
            An additional ``"concentration_acetone"`` field is added by appending a
            further :class:`StateVariableMap` to the sequence.

            .. code-block:: python
                :caption: Python
                :linenos:

                temperature = StateVariableMap("temperature")
                temperature.variable_sphere = "T_pores"
                temperature.variable_cylinder = "T_throats"

                acetone = StateVariableMap("concentration_acetone")
                acetone.variable_sphere = "C_acetone_pores"
                acetone.variable_cylinder = "C_acetone_throats"

                vars_state = [temperature, acetone]

            By convention, the first array dimension is equal to the number of pores/
            throats, while the second dimension contains the evolution of the field, e.g
            in case of the temperature field, it might be the temporal evolution (when
            the pore network contains 6274 pores and 149366 throats, and 1000 temperature
            steps have been calculated, variable ``T_pores`` has a size of ``6274 ×
            1000`` and ``T_throats`` has a size of ``149366 × 1000``).

        no_states : Sequence[int], optional
            In case there is state data contained in the ``.mat`` file, the state indices
            given in ``no_states`` are wrapped into :class:`PoreNetworkState` instances.

            For example, if 1000 states have been calculated, but only every 100th state
            should be visualized, then ``no_states`` could be:

            .. code-block:: python
                :caption: Python
                :linenos:

                no_states = np.linspace(0, 1000, num=10, dtype=int)

        var_time : str | None, optional
            Name of the ``.mat`` variable holding the physical time of every computed
            step. When given, the :attr:`PoreNetworkState.time_point` of each imported
            state is read from this vector at the state's own index, i.e. the same index
            used to select its values from the state variables.

            Computed results are commonly written at irregular intervals, so this vector
            is generally not evenly spaced.

            When ``None`` (default), the states carry no time information and are
            identified by :attr:`PoreNetworkState.no` alone.

        swap_axes : bool, optional
            If ``True`` (default), swaps the first and third columns of every imported
            position array to compensate for the MATLAB/numpy axis-order mismatch
            described above, e.g. aligning coordinates with meshes built by
            :func:`porescene.utility.volume2mesh`. Set to ``False`` to import the
            coordinates verbatim, in the MATLAB axis order.

        Returns
        -------
        Self
            :class:`PoreNetwork` instance created from given ``.mat`` file
        """

        def swap_x_z(a):
            return a[:, [2, 1, 0]] if swap_axes else a

        with File(pth) as f:
            pn = cls()
            if vars_nwk["length_x"] in f:
                pn.length_x = np.array(f[vars_nwk["length_x"]]).item()
            if vars_nwk["length_y"] in f:
                pn.length_y = np.array(f[vars_nwk["length_y"]]).item()
            if vars_nwk["length_z"] in f:
                pn.length_z = np.array(f[vars_nwk["length_z"]]).item()
            if vars_nwk["pore_coordination_number"] in f:
                pn.pore_coordination_number = np.asarray(
                    f[vars_nwk["pore_coordination_number"]]
                ).ravel()
            if vars_nwk["throat_coordination_number"] in f:
                pn.throat_coordination_number = np.asarray(
                    f[vars_nwk["throat_coordination_number"]]
                ).ravel()
            if vars_nwk["pores_top"] in f:
                pn.pores_top = np.array(f[vars_nwk["pores_top"]]).ravel() - 1
            if vars_nwk["pores_bottom"] in f:
                pn.pores_bottom = np.array(f[vars_nwk["pores_bottom"]]).ravel() - 1
            if vars_nwk["pores_left"] in f:
                pn.pores_left = np.array(f[vars_nwk["pores_left"]]).ravel() - 1
            if vars_nwk["pores_right"] in f:
                pn.pores_right = np.array(f[vars_nwk["pores_right"]]).ravel() - 1
            if vars_nwk["pores_front"] in f:
                pn.pores_front = np.array(f[vars_nwk["pores_front"]]).ravel() - 1
            if vars_nwk["pores_back"] in f:
                pn.pores_back = np.array(f[vars_nwk["pores_back"]]).ravel() - 1
            if vars_nwk["pore_position"] in f:
                pn.pore_position = swap_x_z(
                    np.array(f[vars_nwk["pore_position"]]).transpose()
                )
            if vars_nwk["pore_position_top"] in f:
                pn.pore_position_top = swap_x_z(
                    np.array(f[vars_nwk["pore_position_top"]]).transpose()
                )
            if vars_nwk["pore_position_bottom"] in f:
                pn.pore_position_bottom = swap_x_z(
                    np.array(f[vars_nwk["pore_position_bottom"]]).transpose()
                )
            if vars_nwk["pore_position_left"] in f:
                pn.pore_position_left = swap_x_z(
                    np.array(f[vars_nwk["pore_position_left"]]).transpose()
                )
            if vars_nwk["pore_position_right"] in f:
                pn.pore_position_right = swap_x_z(
                    np.array(f[vars_nwk["pore_position_right"]]).transpose()
                )
            if vars_nwk["pore_position_front"] in f:
                pn.pore_position_front = swap_x_z(
                    np.array(f[vars_nwk["pore_position_front"]]).transpose()
                )
            if vars_nwk["pore_position_back"] in f:
                pn.pore_position_back = swap_x_z(
                    np.array(f[vars_nwk["pore_position_back"]]).transpose()
                )
            if vars_nwk["pore_radius"] in f:
                pn.pore_radius = np.array(f[vars_nwk["pore_radius"]]).ravel()
            if "r_p_eqs" in f:  # equivalent-sphere radius overrides r_p if present
                pn.pore_radius = np.array(f["r_p_eqs"]).ravel()
            if vars_nwk["throat_radius"] in f:
                pn.throat_radius = np.array(f[vars_nwk["throat_radius"]]).ravel()
            if vars_nwk["throat_radius_top"] in f:
                pn.throat_radius_top = np.array(f[vars_nwk["throat_radius_top"]]).ravel()
            if vars_nwk["throat_radius_bottom"] in f:
                pn.throat_radius_bottom = np.array(
                    f[vars_nwk["throat_radius_bottom"]]
                ).ravel()
            if vars_nwk["throat_radius_left"] in f:
                pn.throat_radius_left = np.array(
                    f[vars_nwk["throat_radius_left"]]
                ).ravel()
            if vars_nwk["throat_radius_right"] in f:
                pn.throat_radius_right = np.array(
                    f[vars_nwk["throat_radius_right"]]
                ).ravel()
            if vars_nwk["throat_radius_front"] in f:
                pn.throat_radius_front = np.array(
                    f[vars_nwk["throat_radius_front"]]
                ).ravel()
            if vars_nwk["throat_radius_back"] in f:
                pn.throat_radius_back = np.array(
                    f[vars_nwk["throat_radius_back"]]
                ).ravel()
            if vars_nwk["throat_neighboring_pores"] in f:
                pn.throat_neighboring_pores = (
                    np.array(f[vars_nwk["throat_neighboring_pores"]]).transpose() - 1
                )
            if vars_nwk["pore_neighboring_pores"] in f:
                pn.pore_neighboring_pores = (
                    np.array(f[vars_nwk["pore_neighboring_pores"]]).transpose() - 1
                )

        pn.load_states_from_mat(pth, vars_state, no_states, var_time=var_time)
        return pn

    def __iter__(self) -> Iterator[PoreNetworkState]:
        return iter(self.states)

    def __len__(self) -> int:
        """
        Return the number of states in the pore network.
        """
        return len(self.states)

    def __setitem__(self, _, state: PoreNetworkState):
        return self.add_state(state)

    def __getitem__(self, idx: int) -> PoreNetworkState:
        return self.get_state(idx)

    def __str__(self):
        return (
            "PoreNetwork:\n"
            f"  - Domain size: {self.length_x * 1e6:.1f} x "
            f"{self.length_y * 1e6:.1f} x {self.length_z * 1e6:.1f} µm\n"
            # f"  - Pore radius: {self.pore_radius.mean() * 1e6:.2f} µm\n"
            # f"  - Pore radius: {self.throat_radius.mean() * 1e6:.2f} µm\n"
        )

    def add_state(self, no_state: PoreNetworkState) -> Self:
        """
        Adds a :class:`PoreNetworkState` to the current model instance.
        """
        self.states.append(no_state)
        return self

    def frame_times(
        self,
        fps: int = 30,
        *,
        duration: float | None = None,
        speed: float | None = None,
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> np.ndarray:
        """
        Builds the regular grid of times the frames of a video are rendered at.

        Parameters
        ----------
        fps : int, optional
            Playback speed of the video in frames per second, by default 30.
        duration : float | None, optional
            Wall-clock length of the video in seconds. The sampled range is spread over
            exactly ``round(duration * fps)`` frames, with the first and the last frame
            landing on its ends. Mutually exclusive with ``speed``.
        speed : float | None, optional
            Simulated seconds per wall-clock second, by default 1.0, i.e. real time. A
            value of ``60`` plays one simulated minute per second of video. Mutually
            exclusive with ``duration``.
        t_start : float | None, optional
            First frame time, by default the earliest time on the :attr:`time_axis`.
        t_end : float | None, optional
            Time the frames run up to, by default the latest time on the
            :attr:`time_axis`.

        Returns
        -------
        np.ndarray
            Frame times, evenly spaced and ascending.

        Raises
        ------
        ValueError
            If both ``duration`` and ``speed`` are given, if ``fps``, ``duration`` or
            ``speed`` is not positive, if ``t_end`` lies before ``t_start``, or if the
            network holds no states.
        """
        if duration is not None and speed is not None:
            raise ValueError("Give either 'duration' or 'speed', not both")
        if fps <= 0:
            raise ValueError(f"'fps' must be positive, got {fps}")

        times = self.time_axis
        if len(times) == 0:
            raise ValueError("Cannot build frame times for a PoreNetwork without states")

        t0 = float(times[0]) if t_start is None else float(t_start)
        t1 = float(times[-1]) if t_end is None else float(t_end)
        if t1 < t0:
            raise ValueError(f"'t_end' ({t1}) lies before 't_start' ({t0})")

        if duration is not None:
            if duration <= 0:
                raise ValueError(f"'duration' must be positive, got {duration}")
            return np.linspace(t0, t1, max(round(duration * fps), 1))

        speed = 1.0 if speed is None else speed
        if speed <= 0:
            raise ValueError(f"'speed' must be positive, got {speed}")
        step = speed / fps
        return t0 + np.arange(floor((t1 - t0) / step) + 1) * step

    def frames(
        self,
        fps: int = 30,
        *,
        duration: float | None = None,
        speed: float | None = None,
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> Iterator[PoreNetworkState]:
        """
        Resamples the network onto a regular grid of frame times.

        Computed results are commonly written at irregular intervals, while a video
        needs frames at regular ones. This walks the frame times of
        :meth:`frame_times` and evaluates the network at each of them with
        :meth:`state_at`, so that frame times -- rather than stored sample indices --
        drive the rendering.

        The states are produced lazily, so a long sequence never holds more than the
        frame currently being rendered.

        The parameters are those of :meth:`frame_times`.

        .. code-block:: python
            :caption: Python
            :linenos:

            # a 12 second video of the whole series at 30 fps
            for st in pn.frames(fps=30, duration=12):
                ...

        Yields
        ------
        PoreNetworkState
            The state of the network at each frame time.
        """
        for t in self.frame_times(
            fps, duration=duration, speed=speed, t_start=t_start, t_end=t_end
        ):
            yield self.state_at(float(t))

    def get_state(self, no_state: int) -> PoreNetworkState:
        """
        Returns a :class:`PoreNetworkState` from the instance.
        """
        return self.states[no_state]

    def has_quantity(self, name: str) -> bool:
        """
        Whether any state of the network carries a quantity named ``name``.

        The counterpart to :meth:`PoreNetworkState.has_quantity`, which covers one
        state alone: states are free to carry different quantities, so the network
        holds one as soon as a single state does. This is the question
        :meth:`quantity_min` and :meth:`quantity_max` are answered from -- both raise
        wherever this returns ``False``.

        The geometry quantities ``"radius"`` and ``"coordination_number"`` are held by
        the network once rather than per state, so they are reported as missing here
        even though a scene can be colored by them, see
        :func:`porescene.worker.quantity_range`.

        Parameters
        ----------
        name : str
            Name of the quantity, see :attr:`PoreNetworkQuantity.name`.

        Returns
        -------
        bool
            ``True`` if at least one state carries the quantity.
        """
        return any(st.has_quantity(name) for st in self.states)

    def load_states_from_mat(
        self,
        pth_mat: Path,
        vars_state: Sequence[StateVariableMap],
        no_states: Sequence[int],
        *,
        var_time: str | None = None,
    ) -> Self:
        """
        Loads state data from a MATLAB ``.mat`` file into this instance.

        In contrast to :meth:`from_mat`, which builds a new :class:`PoreNetwork`, this
        method appends the requested states to an already existing instance, loading both
        pore and throat data for each :class:`PoreNetworkQuantity`.

        .. attention::

            Variable import from ``.mat`` files is only supported for MATLAB files in
            version 7.3 that are based on `HDF5 <https://github.com/HDFGroup/hdf5>`_.
            When saving the MATLAB file, make sure to set the ``-v7.3`` in MATLAB's
            ``save`` function.

        Parameters
        ----------
        pth_mat : Path
            Path to the MATLAB ``.mat`` file.
        vars_state : Sequence[StateVariableMap]
            The :class:`StateVariableMap` instances that relate the state variables in
            the ``.mat`` file to :class:`PoreNetworkQuantity` instances. Each map carries
            a quantity name (:attr:`StateVariableMap.name`) together with the names of
            the ``.mat`` variables holding the per-pore and per-throat data
            (:attr:`StateVariableMap.variable_sphere` and
            :attr:`StateVariableMap.variable_cylinder`, respectively). A variable left as
            ``None`` is skipped, so a quantity may provide pore data, throat data, or
            both.
        no_states : Sequence[int]
            State indices that are wrapped into :class:`PoreNetworkState` instances and
            appended to this :class:`PoreNetwork`.
        var_time : str | None, optional
            Name of the ``.mat`` variable holding the physical time of every computed
            step. When given, the :attr:`PoreNetworkState.time_point` of each loaded
            state is read from this vector at the state's own index. When ``None``
            (default), the states carry no time information and are identified by
            :attr:`PoreNetworkState.no` alone.

        Returns
        -------
        Self
            This :class:`PoreNetwork` instance with the loaded states added.

        Raises
        ------
        ValueError
            If a non-``None`` pore or throat variable named in ``vars_state`` is not
            present in the ``.mat`` file, if ``var_time`` is not present in the ``.mat``
            file, or if a state index in ``no_states`` lies outside the time vector.
        """

        with File(pth_mat) as f:
            time_points = None
            if var_time is not None:
                if var_time not in f:
                    raise ValueError(
                        f"Could not find variable '{var_time}' in given .mat file"
                    )
                time_points = np.asarray(f[var_time]).ravel()

            for state in no_states:
                st = PoreNetworkState(no=state)

                # a time point is optional; without it the state is known by its index
                if time_points is not None:
                    if state >= len(time_points):
                        raise ValueError(
                            f"State index {state} is out of range for the "
                            f"{len(time_points)} time points in '{var_time}'"
                        )
                    st.time_point = time_points[state].item()

                for svm in vars_state:
                    pn_quant = PoreNetworkQuantity(svm.name, svm.interpolation)

                    # load pore (sphere) data (skipped when no variable is given)
                    if svm.variable_sphere is not None:
                        if svm.variable_sphere not in f:
                            raise ValueError(
                                "Could not find variable "
                                f"'{svm.variable_sphere}' in given .mat file"
                            )
                        pn_quant.pore_values = np.array(
                            f[svm.variable_sphere][state, :]
                        ).transpose()

                    # load throat (cylinder) data (skipped when no variable is given)
                    if svm.variable_cylinder is not None:
                        if svm.variable_cylinder not in f:
                            raise ValueError(
                                "Could not find variable "
                                f"'{svm.variable_cylinder}' in given .mat file"
                            )
                        pn_quant.throat_values = np.array(
                            f[svm.variable_cylinder][state, :]
                        ).transpose()

                    st.add_quantity(pn_quant)
                self.add_state(st)
            return self

    def quantity_max(self, name: str) -> float:
        """
        Highest value of the quantity ``name`` over all states of the network.

        The counterpart to :attr:`PoreNetworkQuantity.max`, which covers one state
        alone: this spans the whole series, so that every frame of a video can share
        one set of colour boundaries instead of rescaling from state to state. It also
        bounds the states :meth:`state_at` returns, since interpolation never leaves
        the range of the stored states it blends.

        States that do not carry the quantity are skipped, and ``NaN`` values are
        ignored.

        Parameters
        ----------
        name : str
            Name of the quantity, see :attr:`PoreNetworkQuantity.name`.

        Returns
        -------
        float
            Highest value across the pores and throats of all states.

        Raises
        ------
        ValueError
            If no state of the network carries a quantity named ``name``.
        """
        return float(np.nanmax([q.max for q in self._quantities_named(name)]))

    def quantity_min(self, name: str) -> float:
        """
        Lowest value of the quantity ``name`` over all states of the network.

        The counterpart to :attr:`PoreNetworkQuantity.min`, see :meth:`quantity_max`.

        Parameters
        ----------
        name : str
            Name of the quantity, see :attr:`PoreNetworkQuantity.name`.

        Returns
        -------
        float
            Lowest value across the pores and throats of all states.

        Raises
        ------
        ValueError
            If no state of the network carries a quantity named ``name``.
        """
        return float(np.nanmin([q.min for q in self._quantities_named(name)]))

    def state_at(self, t: float) -> PoreNetworkState:
        """
        Returns the state of the network at time ``t``, interpolating between the stored
        states where needed.

        The counterpart to :meth:`get_state`, which picks a stored state by its
        position: this evaluates the network anywhere on its :attr:`time_axis`,
        including between two stored states.

        Times outside the sampled range are clamped, i.e. the first and the last stored
        state are held rather than extrapolated. Times falling between two stored states
        are resolved per quantity, following each quantity's
        :attr:`~PoreNetworkQuantity.interpolation`, so a saturation field can be held
        between samples while a temperature field is blended, within one and the same
        frame.

        .. attention::

            The returned state may share its value arrays with the stored states instead
            of copying them, which keeps a long frame sequence from duplicating every
            field. Treat it as read-only.

        Parameters
        ----------
        t : float
            Point on the :attr:`time_axis` to evaluate.

        Returns
        -------
        PoreNetworkState
            State carrying ``t`` as its :attr:`~PoreNetworkState.time_point`. Its
            :attr:`~PoreNetworkState.no` is that of the stored state at or before ``t``,
            i.e. the step the frame is based on.

        Raises
        ------
        ValueError
            If the network holds no states, or a quantity carries an unknown
            interpolation mode.
        """
        states, times = self._time_ordered()
        if len(times) == 0:
            raise ValueError("Cannot evaluate a PoreNetwork that holds no states")

        # outside the stored range the nearest state is held, only restamped onto ``t``
        if t <= times[0]:
            return PoreNetworkState(states[0].quantities, states[0].no, t)
        if t >= times[-1]:
            return PoreNetworkState(states[-1].quantities, states[-1].no, t)

        hi = int(np.searchsorted(times, t, side="right"))
        lo = hi - 1

        # guards against a zero-width interval, e.g. a state selected twice
        span = times[hi] - times[lo]
        w = 0.0 if span == 0 else float((t - times[lo]) / span)

        st_lo = states[lo]
        st_hi = states[hi]

        out = PoreNetworkState(no=st_lo.no, time_point=t)
        for quant in st_lo.quantities:
            other = (
                st_hi.get_quantity(quant.name) if st_hi.has_quantity(quant.name) else None
            )
            out.add_quantity(PoreNetwork._resolve(quant, other, w))
        return out

    def _quantities_named(self, name: str) -> list[PoreNetworkQuantity]:
        """
        The quantity ``name`` of every state carrying it, in :attr:`states` order.

        States are free to carry different quantities, so this skips the ones the
        quantity is missing from rather than treating them as a gap.
        """
        quants = [st.get_quantity(name) for st in self.states if st.has_quantity(name)]
        if not quants:
            raise ValueError(f"No state carries a quantity named '{name}'")
        return quants

    def _time_ordered(self) -> tuple[list[PoreNetworkState], np.ndarray]:
        """
        The states paired with the time axis they sit on, both in ascending time order.

        :attr:`states` itself keeps the order the states were added in; only this view
        is sorted, so that resampling stays correct even for states added out of order.
        """
        times = self._raw_times()
        order = np.argsort(times, kind="stable")
        return [self.states[i] for i in order], times[order]

    def _raw_times(self) -> np.ndarray:
        """
        The time axis in :attr:`states` order, i.e. not necessarily ascending.
        """
        if self.has_time_points:
            return np.array([st.time_point for st in self.states], dtype=float)
        nos = [st.no for st in self.states]
        if nos and all(no is not None for no in nos):
            return np.array(nos, dtype=float)
        return np.arange(len(self.states), dtype=float)

    @staticmethod
    def _resolve(
        p_lo: PoreNetworkQuantity,
        p_hi: PoreNetworkQuantity | None,
        w: float,
    ) -> PoreNetworkQuantity:
        """
        Resolves one quantity between two stored states, ``w`` being the normalized
        distance from the earlier state to the later one.

        ``p_hi`` is ``None`` when the later state does not carry the quantity, in which
        case the earlier one is held.
        """
        mode = p_lo.interpolation
        if p_hi is None or mode is InterpolationType.PREVIOUS:
            return p_lo
        if mode is InterpolationType.NEAREST:
            return p_lo if w < 0.5 else p_hi
        if mode is not InterpolationType.LINEAR:
            raise ValueError(f"Unknown interpolation mode '{mode}'")
        return PoreNetworkQuantity(p_lo.name, mode).set_data(
            _lerp(p_lo.pore_values, p_hi.pore_values, w),
            _lerp(p_lo.throat_values, p_hi.throat_values, w),
        )

    @property
    def length_x(self) -> float:
        """
        Physical extent of the pore network domain in first dimension.
        """
        return self._length_x

    @length_x.setter
    def length_x(self, arg: float):
        self._length_x = arg

    @property
    def length_y(self) -> float:
        """
        Physical extent of the pore network domain in second dimension.
        """
        return self._length_y

    @length_y.setter
    def length_y(self, arg: float):
        self._length_y = arg

    @property
    def length_z(self) -> float:
        """
        Physical extent of the pore network domain in third dimension.
        """
        return self._length_z

    @length_z.setter
    def length_z(self, arg: float):
        self._length_z = arg

    @property
    def pore_coordination_number(self) -> np.ndarray | None:
        """
        Coordination number of each pore.
        """
        return self._pore_coordination_number

    @pore_coordination_number.setter
    def pore_coordination_number(self, arg: np.ndarray | None):
        self._pore_coordination_number = arg

    @property
    def pore_count(self) -> int:
        """
        Number of pores in the network.
        """
        if self.pore_radius is not None:
            cnt = len(self.pore_radius)
        else:
            cnt = 0
        return cnt

    @property
    def pore_neighboring_pores(self) -> np.ndarray | None:
        """
        Neighbor pores of each pore.
        """
        return self._pore_neighboring_pores

    @pore_neighboring_pores.setter
    def pore_neighboring_pores(self, arg: np.ndarray | None):
        self._pore_neighboring_pores = arg

    @property
    def pnp(self) -> np.ndarray | None:
        """
        Neighbor pores of each pore.
        """
        return self._pore_neighboring_pores

    @property
    def pore_position(self) -> np.ndarray | None:
        """
        Position of each pore.
        """
        return self._pore_position

    @pore_position.setter
    def pore_position(self, arg: np.ndarray | None):
        self._pore_position = arg

    @property
    def pore_position_left(self) -> np.ndarray | None:
        """
        Position of each node at the left sample surface.
        """
        return self._pore_position_left

    @pore_position_left.setter
    def pore_position_left(self, arg: np.ndarray | None):
        self._pore_position_left = arg

    @property
    def pore_position_right(self) -> np.ndarray | None:
        """
        Position of each node at the right sample surface.
        """
        return self._pore_position_right

    @pore_position_right.setter
    def pore_position_right(self, arg: np.ndarray | None):
        self._pore_position_right = arg

    @property
    def pore_position_front(self) -> np.ndarray | None:
        """
        Position of each node at the sample bottom surface.
        """
        return self._pore_position_front

    @pore_position_front.setter
    def pore_position_front(self, arg: np.ndarray | None):
        self._pore_position_front = arg

    @property
    def pore_position_back(self) -> np.ndarray | None:
        """
        Position of each node at the sample bottom surface.
        """
        return self._pore_position_back

    @pore_position_back.setter
    def pore_position_back(self, arg: np.ndarray | None):
        self._pore_position_back = arg

    @property
    def pore_position_bottom(self) -> np.ndarray | None:
        """
        Position of each node at the sample bottom surface.
        """
        return self._pore_position_bottom

    @pore_position_bottom.setter
    def pore_position_bottom(self, arg: np.ndarray | None):
        self._pore_position_bottom = arg

    @property
    def pore_position_top(self) -> np.ndarray | None:
        """
        Position of each node at the top sample surface.
        """
        return self._pore_position_top

    @pore_position_top.setter
    def pore_position_top(self, arg: np.ndarray | None):
        self._pore_position_top = arg

    @property
    def pore_radius(self) -> np.ndarray | None:
        """
        Radius of each pore.
        """
        return self._pore_radius

    @pore_radius.setter
    def pore_radius(self, arg: np.ndarray | None):
        self._pore_radius = arg

    @property
    def pores_top(self) -> np.ndarray | None:
        """
        Pores located at the sample top interface that have a connection to the
        surrounding.
        """
        return self._pores_top

    @pores_top.setter
    def pores_top(self, arg: np.ndarray | None):
        self._pores_top = arg

    @property
    def pores_bottom(self) -> np.ndarray | None:
        """
        Pores located at the sample bottom interface that have a connection to the
        surrounding.
        """
        return self._pores_bottom

    @pores_bottom.setter
    def pores_bottom(self, arg: np.ndarray | None):
        self._pores_bottom = arg

    @property
    def pores_left(self) -> np.ndarray | None:
        """
        Pores located at the left domain interface that have a connection to the
        surrounding.
        """
        return self._pores_left

    @pores_left.setter
    def pores_left(self, arg: np.ndarray | None):
        self._pores_left = arg

    @property
    def pores_right(self) -> np.ndarray | None:
        """
        Pores located at the right domain interface that have a connection to the
        surrounding.
        """
        return self._pores_right

    @pores_right.setter
    def pores_right(self, arg: np.ndarray | None):
        self._pores_right = arg

    @property
    def pores_front(self) -> np.ndarray | None:
        """
        Pores located at the front domain interface that have a connection to the
        surrounding.
        """
        return self._pores_front

    @pores_front.setter
    def pores_front(self, arg: np.ndarray | None):
        self._pores_front = arg

    @property
    def pores_back(self) -> np.ndarray | None:
        """
        Pores located at the back domain interface that have a connection to the
        surrounding.
        """
        return self._pores_back

    @pores_back.setter
    def pores_back(self, arg: np.ndarray | None):
        self._pores_back = arg

    @property
    def extent(self) -> np.ndarray:
        """
        Physical dimensions (x, y, z) of the pore network domain.
        """
        return np.array([self.length_x, self.length_y, self.length_z])

    @property
    def states(self) -> list[PoreNetworkState]:
        """
        The states of the pore network.
        """
        return self._states

    @states.setter
    def states(self, arg: list[PoreNetworkState]):
        self._states = arg

    @property
    def has_time_points(self) -> bool:
        """
        Whether every state of the pore network carries a physical time.

        ``False`` for a network without states, or when at least one state was imported
        without time information, in which case :attr:`time_axis` falls back to a
        substitute axis.
        """
        return len(self.states) > 0 and all(
            st.time_point is not None for st in self.states
        )

    @property
    def time_axis(self) -> np.ndarray:
        """
        The axis :meth:`state_at` and :meth:`frames` resample the network along,
        ascending.

        Built from the :attr:`~PoreNetworkState.time_point` of every state when they all
        carry one. Otherwise the states' :attr:`~PoreNetworkState.no` indices stand in,
        which spaces them correctly as long as the computed steps they were selected
        from are themselves evenly spaced -- selecting states ``(0, 500, 600, 930)`` then
        still yields the right relative spacing, even though no time is known. As a last
        resort, for states carrying neither, the position in :attr:`states` is used and
        the states are treated as evenly spaced.

        In contrast to :attr:`time_points`, which reports the stored times verbatim,
        this is always a usable axis and always ascending.

        .. attention::

            Only the first case reflects the real timing of the results. Import a time
            vector via the ``var_time`` argument of :meth:`from_mat` whenever the
            computed steps are not evenly spaced, otherwise a video built from this axis
            plays back at the wrong speed. :attr:`has_time_points` reports which case
            applies.
        """
        return self._time_ordered()[1]

    @property
    def time_points(self) -> list[float | None]:
        """
        Physical time of each state, in :attr:`states` order.

        Entries are ``None`` for states that carry no time information, see
        :attr:`has_time_points`. Use :attr:`time_axis` for the resolved axis that
        resampling runs on.
        """
        return [st.time_point for st in self.states]

    @property
    def throat_coordination_number(self) -> np.ndarray | None:
        """
        Coordination number of each throat.
        """
        return self._throat_coordination_number

    @throat_coordination_number.setter
    def throat_coordination_number(self, arg: np.ndarray | None):
        self._throat_coordination_number = arg

    def throat_count(
        self,
        left: bool = False,
        right: bool = False,
        front: bool = False,
        back: bool = False,
        bottom: bool = False,
        top: bool = False,
    ) -> int:
        """
        Number of throats in the network.

        Parameters
        ----------
        left : bool, optional
            If true, outgoing throats on the left domain boundary are included in the
            throat count, by default False.
        right : bool, optional
            If true, outgoing throats on the right domain boundary are included in the
            throat count, by default False.
        front : bool, optional
            If true, outgoing throats on the front domain boundary are included in the
            throat count, by default False.
        back : bool, optional
            If true, outgoing throats on the back domain boundary are included in the
            throat count, by default False.
        bottom : bool, optional
            If true, outgoing throats on the bottom domain boundary are included in the
            throat count, by default False.
        top : bool, optional
            If true, outgoing throats on the top domain boundary are included in the
            throat count, by default False.

        Returns
        -------
        int
            Number of throats.
        """
        if self.throat_radius is not None:
            cnt = len(self.throat_radius)
            if top and self.throat_radius_top is not None:
                cnt += len(self.throat_radius_top)
            if bottom and self.throat_radius_bottom is not None:
                cnt += len(self.throat_radius_bottom)
            if left and self.throat_radius_left is not None:
                cnt += len(self.throat_radius_left)
            if right and self.throat_radius_right is not None:
                cnt += len(self.throat_radius_right)
            if front and self.throat_radius_front is not None:
                cnt += len(self.throat_radius_front)
            if back and self.throat_radius_back is not None:
                cnt += len(self.throat_radius_back)
        else:
            cnt = 0
        return cnt

    @property
    def throat_length(self) -> np.ndarray | None:
        """
        Length of each throat.
        """
        return self._throat_length

    @throat_length.setter
    def throat_length(self, arg: np.ndarray | None):
        self._throat_length = arg

    @property
    def throat_radius(self) -> np.ndarray | None:
        """
        Radius of each throat.
        """
        return self._throat_radius

    @throat_radius.setter
    def throat_radius(self, arg: np.ndarray | None):
        self._throat_radius = arg

    @property
    def throat_radius_top(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the top domain
        boundary.
        """
        return self._throat_radius_top

    @throat_radius_top.setter
    def throat_radius_top(self, arg: np.ndarray | None):
        self._throat_radius_top = arg

    @property
    def throat_radius_bottom(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the bottom domain
        boundary.
        """
        return self._throat_radius_bot

    @throat_radius_bottom.setter
    def throat_radius_bottom(self, arg: np.ndarray | None):
        self._throat_radius_bot = arg

    @property
    def throat_radius_left(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the left domain
        boundary.
        """
        return self._throat_radius_left

    @throat_radius_left.setter
    def throat_radius_left(self, arg: np.ndarray | None):
        self._throat_radius_left = arg

    @property
    def throat_radius_right(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the right domain
        boundary.
        """
        return self._throat_radius_right

    @throat_radius_right.setter
    def throat_radius_right(self, arg: np.ndarray | None):
        self._throat_radius_right = arg

    @property
    def throat_radius_front(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the front domain
        boundary.
        """
        return self._throat_radius_front

    @throat_radius_front.setter
    def throat_radius_front(self, arg: np.ndarray | None):
        self._throat_radius_front = arg

    @property
    def throat_radius_back(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the back domain
        boundary.
        """
        return self._throat_radius_back

    @throat_radius_back.setter
    def throat_radius_back(self, arg: np.ndarray | None):
        self._throat_radius_back = arg

    @property
    def throat_neighboring_pores(self) -> np.ndarray | None:
        """
        Neighbor pores of each throat.
        """
        return self._throat_neighboring_pores

    @throat_neighboring_pores.setter
    def throat_neighboring_pores(self, arg: np.ndarray | None):
        self._throat_neighboring_pores = arg

    @property
    def tnp(self) -> np.ndarray | None:
        """
        Neighbor pores of each throat.
        """
        return self._throat_neighboring_pores


def _lerp(a: np.ndarray | None, b: np.ndarray | None, w: float) -> np.ndarray | None:
    """
    Blends two value arrays, weighting ``b`` by ``w``.

    ``None`` on either side means the quantity does not carry that kind of data, so
    ``a`` is passed through unchanged. ``NaN`` is deliberately not special-cased: it
    marks a value the simulation did not define (e.g. the vapour pressure of a dry
    pore), and letting it propagate keeps the gap visible instead of papering over it
    with a neighbouring value.
    """
    if a is None or b is None:
        return a
    return a + (b - a) * w
