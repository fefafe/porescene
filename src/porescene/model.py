# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

"""
Pore Networks
"""

from pathlib import Path
from typing import Self

import numpy as np
from h5py import File


class PoreNetworkProperty:
    """
    A wrapper for a single property of one state of a pore network.
    """

    def __init__(self, n: str) -> None:
        self.name = n
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
    def name(self) -> str:
        """Name of the property."""
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
    """

    def __init__(self) -> None:
        self._properties = []

    def __iter__(self) -> Self:
        self.__i = 0
        return self

    def __len__(self) -> int:
        return len(self.properties)

    def __next__(self) -> PoreNetworkProperty:
        if self.__i < len(self.properties) and self.__i >= 0:
            prop = self.properties[self.__i]
            self.__i += 1
            return prop
        else:
            raise StopIteration

    def __setitem__(self, _, prop: PoreNetworkProperty):
        return self.add_property(prop)

    def __getitem__(self, idx: str) -> PoreNetworkProperty:
        return self.get_property(idx)

    def add_property(self, prop: PoreNetworkProperty) -> Self:
        """
        Add a :class:`PoreNetworkProperty`.
        """
        if self.has_property(prop.name):
            self.properties[self._property_index(prop.name)] = prop
        else:
            self._properties.append(prop)
        return self

    def get_property(self, name: str) -> PoreNetworkProperty:
        """
        Returns a :class:`PoreNetworkProperty` by name.
        """
        return self.properties[self._property_index(name)]

    def has_property(self, name: str) -> bool:
        """
        Check if the model has data about property `name`.
        """
        for prop in self.properties:
            if prop.name == name:
                return True
        return False

    def _property_index(self, name) -> int:
        if not self.has_property(name):
            raise ValueError(f"Could not find a property named '{name}'")
        idx = -1
        for i, prop in enumerate(self._properties):
            if prop.name == name:
                idx = i
        return idx

    @property
    def time_points(self) -> list[float]:
        return self._time_points

    @time_points.setter
    def time_points(self, arg: list[float]) -> Self:
        self._time_points = arg
        return self

    @property
    def no(self) -> int:
        return self._no

    @no.setter
    def no(self, arg: int) -> Self:
        self._no = arg
        return self

    @property
    def properties(self) -> list[PoreNetworkProperty]:
        return self._properties

    @time_points.setter
    def time_points(self, arg: list[PoreNetworkProperty]) -> Self:
        self._properties = arg
        return self


class PoreNetwork:

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
        states: list[int] = [],
        state_vars: dict[str, tuple[str, str]] = {},
    ) -> Self:
        with File(pth) as f:
            pn = cls()
            if "L_sample_x" in f:
                pn.length_x = np.array(f["L_sample_x"]).item()
            if "L_sample_y" in f:
                pn.length_y = np.array(f["L_sample_y"]).item()
            if "L_sample_z" in f:
                pn.length_z = np.array(f["L_sample_z"]).item()
            if "cn_p" in f:
                pn.pore_coordination_number = np.array(f["cn_p"]).transpose()
            if "cn_t" in f:
                pn.throat_coordination_number = np.array(f["cn_t"]).transpose()
            if "p_top" in f:
                pn.pores_top = np.array(f["p_top"]).flatten() - 1
            if "p_bot" in f:
                pn.pores_bot = np.array(f["p_bot"]).flatten() - 1
            if "p_left" in f:
                pn.pores_left = np.array(f["p_left"]).flatten() - 1
            if "p_right" in f:
                pn.pores_right = np.array(f["p_right"]).flatten() - 1
            if "p_front" in f:
                pn.pores_front = np.array(f["p_front"]).flatten() - 1
            if "p_back" in f:
                pn.pores_back = np.array(f["p_back"]).flatten() - 1
            if "pos_p" in f:
                pn.pore_position = np.array(f["pos_p"]).transpose()
            if "pos_p_out_top" in f:
                pn.pore_position_top = np.array(f["pos_p_out_top"]).transpose()
            if "pos_p_out_bot" in f:
                pn.pore_position_bot = np.array(f["pos_p_out_bot"]).transpose()
            if "pos_p_out_left" in f:
                pn.pore_position_left = np.array(f["pos_p_out_left"]).transpose()
            if "pos_p_out_right" in f:
                pn.pore_position_right = np.array(f["pos_p_out_right"]).transpose()
            if "pos_p_out_front" in f:
                pn.pore_position_front = np.array(f["pos_p_out_front"]).transpose()
            if "pos_p_out_back" in f:
                pn.pore_position_back = np.array(f["pos_p_out_back"]).transpose()
            if "r_p" in f:
                pn.pore_radius = np.array(f["r_p"]).transpose()
            if "r_p_eqs" in f:
                pn.pore_radius = np.array(f["r_p_eqs"]).transpose()
            if "r_t" in f:
                pn.throat_radius = np.array(f["r_t"]).transpose()
            if "r_t_out_top" in f:
                pn.throat_radius_top = np.array(f["r_t_out_top"]).transpose()
            if "r_t_out_bot" in f:
                pn.throat_radius_bottom = np.array(f["r_t_out_bot"]).transpose()
            if "r_t_out_left" in f:
                pn.throat_radius_left = np.array(f["r_t_out_left"]).transpose()
            if "r_t_out_right" in f:
                pn.throat_radius_right = np.array(f["r_t_out_right"]).transpose()
            if "r_t_out_front" in f:
                pn.throat_radius_front = np.array(f["r_t_out_front"]).transpose()
            if "r_t_out_back" in f:
                pn.throat_radius_back = np.array(f["r_t_out_back"]).transpose()
            if "tnp" in f:
                pn.throat_neighboring_pores = np.array(f["tnp"]).transpose() - 1
            if "pnp" in f:
                pn.pore_neighboring_pores = np.array(f["pnp"])
            for state in states:
                st = PoreNetworkState()
                st.no = state
                for name, var in state_vars.items():
                    pn_prop = PoreNetworkProperty(name)
                    if var[0] in f:
                        pn_prop.pore_values = np.array(f[var[0]][state, :]).transpose()
                    else:
                        raise ValueError(
                            f"Could not find variable '{var[0]}' in given .mat file"
                        )
                    st.add_property(pn_prop)
                pn.add_state(st)
            return pn

    def __iter__(self) -> Self:
        self.__i = 0
        return self

    def __len__(self) -> int:
        """
        Return the number of colors of the gradient.
        """
        return len(self.states)

    def __next__(self) -> PoreNetworkState:
        if self.__i < len(self.states) and self.__i >= 0:
            st = self.states[self.__i]
            self.__i += 1
            return st
        else:
            raise StopIteration

    def __setitem__(self, _, prop: PoreNetworkState):
        return self.add_state(prop)

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

    def add_state(self, st: PoreNetworkState) -> Self:
        """
        Add a :class:`PoreNetworkState` to the current model instance.
        """
        self.states.append(st)
        return self

    def get_state(self, idx: int) -> PoreNetworkState:
        """
        Returns a :class:`PoreNetworkProperty` from the instance.
        """
        return self.states[idx]

    @property
    def length_x(self) -> float:
        """
        Radius of each throat.
        """
        return self._length_x

    @length_x.setter
    def length_x(self, arg: float):
        self._length_x = arg

    @property
    def length_y(self) -> float:
        """
        Radius of each throat.
        """
        return self._length_y

    @length_y.setter
    def length_y(self, arg: float):
        self._length_y = arg

    @property
    def length_z(self) -> float:
        """
        Radius of each throat.
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
        Neighbor pores of each throat.
        """
        return self._pore_neighboring_pores

    @pore_neighboring_pores.setter
    def pore_neighboring_pores(self, arg: np.ndarray | None):
        self._pore_neighboring_pores = arg

    @property
    def pnp(self) -> np.ndarray | None:
        """
        Neighbor pores of each throat.
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
    def pore_position_bot(self) -> np.ndarray | None:
        """
        Position of each node at the sample bottom surface.
        """
        return self._pore_position_bot

    @pore_position_bot.setter
    def pore_position_bot(self, arg: np.ndarray | None):
        self._pore_position_bot = arg

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
    def pores_bot(self) -> np.ndarray | None:
        """
        Pores located at the sample bot interface that have a connection to the
        surrounding.
        """
        return self._pores_bot

    @pores_bot.setter
    def pores_bot(self, arg: np.ndarray | None):
        self._pores_bot = arg

    @property
    def pores_left(self) -> np.ndarray | None:
        """
        Pores located at the sample left interface that have a connection to the
        surrounding.
        """
        return self._pores_left

    @pores_left.setter
    def pores_left(self, arg: np.ndarray | None):
        self._pores_left = arg

    @property
    def pores_right(self) -> np.ndarray | None:
        """
        Pores located at the sample right interface that have a connection to the
        surrounding.
        """
        return self._pores_right

    @pores_right.setter
    def pores_right(self, arg: np.ndarray | None):
        self._pores_right = arg

    @property
    def pores_front(self) -> np.ndarray | None:
        """
        Pores located at the sample front interface that have a connection to the
        surrounding.
        """
        return self._pores_front

    @pores_front.setter
    def pores_front(self, arg: np.ndarray | None):
        self._pores_front = arg

    @property
    def pores_back(self) -> np.ndarray | None:
        """
        Pores located at the sample back interface that have a connection to the
        surrounding.
        """
        return self._pores_back

    @pores_back.setter
    def pores_back(self, arg: np.ndarray | None):
        self._pores_back = arg

    @property
    def extent(self) -> np.ndarray:
        """ """
        return np.array([self.length_x, self.length_y, self.length_z])

    @property
    def states(self) -> list[PoreNetworkState]:
        """ """
        return self._states

    @states.setter
    def states(self, arg: list[PoreNetworkState]):
        self._states = arg

    @property
    def throat_coordination_number(self) -> np.ndarray | None:
        """
        Coordination number of each throat.
        """
        return self._throat_coordination_number

    @throat_coordination_number.setter
    def throat_coordination_number(self, arg: np.ndarray | None):
        self._throat_coordination_number = arg

    @property
    def throat_count(self) -> int:
        """
        Number of throats in the network.
        """
        if self.throat_radius is not None:
            cnt = len(self.throat_radius)
            if self.throat_radius_top is not None:
                cnt += len(self.throat_radius_top)
            if self.throat_radius_bot is not None:
                cnt += len(self.throat_radius_bot)
            if self.throat_radius_left is not None:
                cnt += len(self.throat_radius_left)
            if self.throat_radius_right is not None:
                cnt += len(self.throat_radius_right)
            if self.throat_radius_front is not None:
                cnt += len(self.throat_radius_front)
            if self.throat_radius_back is not None:
                cnt += len(self.throat_radius_back)
        else:
            cnt = 0
        return cnt

    @property
    def throat_length(self) -> np.ndarray | None:
        """
        Radius of each throat.
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
        Radius of each throat connection into the surrounding at the sample top
        interface.
        """
        return self._throat_radius_top

    @throat_radius_top.setter
    def throat_radius_top(self, arg: np.ndarray | None):
        self._throat_radius_top = arg

    @property
    def throat_radius_bottom(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the sample top
        interface.
        """
        return self._throat_radius_bot

    @throat_radius_bottom.setter
    def throat_radius_bottom(self, arg: np.ndarray | None):
        self._throat_radius_bot = arg

    @property
    def throat_radius_left(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the sample left
        interface.
        """
        return self._throat_radius_left

    @throat_radius_left.setter
    def throat_radius_left(self, arg: np.ndarray | None):
        self._throat_radius_left = arg

    @property
    def throat_radius_right(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the sample right
        interface.
        """
        return self._throat_radius_right

    @throat_radius_right.setter
    def throat_radius_right(self, arg: np.ndarray | None):
        self._throat_radius_right = arg

    @property
    def throat_radius_front(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the sample front
        interface.
        """
        return self._throat_radius_front

    @throat_radius_front.setter
    def throat_radius_front(self, arg: np.ndarray | None):
        self._throat_radius_front = arg

    @property
    def throat_radius_back(self) -> np.ndarray | None:
        """
        Radius of each throat connection into the surrounding at the sample back
        interface.
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
