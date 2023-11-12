'''Chemical Engineering Design Library (ChEDL). Utilities for process modeling.
Copyright (C) 2016, 2017, 2018, 2019, 2020 Caleb Bell <Caleb.Andrew.Bell@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from fluids.numerics import derivative, linspace
from fluids.numerics import numpy as np

from thermo.utils.functional import has_matplotlib
from thermo.utils.names import NEGLECT_P
from thermo.utils.t_dependent_property import TDependentProperty

__all__ = ['TPDependentProperty']

class TPDependentProperty(TDependentProperty):
    '''Class for calculating temperature and pressure dependent chemical
    properties.

    On creation, a :obj:`TPDependentProperty` examines all the possible methods
    implemented for calculating the property, loads whichever coefficients it
    needs (unless `load_data` is set to False), examines its input parameters,
    and selects the method it prefers. This method will continue to be used for
    all calculations until the method is changed by setting a new method
    to the to :obj:`method` attribute.

    Because many pressure dependent property methods are implemented as a
    low-pressure correlation and a high-pressure correlation, this class
    works essentially the same as :obj:`TDependentProperty` but with extra
    methods that accept pressure as a parameter.

    The object also selects the pressure-dependent method it prefers.
    This method will continue to be used for all pressure-dependent
    calculations until the pressure-dependent method is changed by setting a
    new method_P to the to :obj:`method_P` attribute.

    The default list of preferred pressure-dependent method orderings is at
    :obj:`ranked_methods_P`
    for all properties; the order can be modified there in-place, and this
    will take effect on all new :obj:`TPDependentProperty` instances created
    but NOT on existing instances.

    Tabular data can be provided as either temperature-dependent or
    pressure-dependent data. The same `extrapolation` settings as in
    :obj:`TDependentProperty` are implemented here for the low-pressure
    correlations.

    In addition to the methods and attributes shown here, all those from
    :obj:`TPDependentProperty` are also available.

    Attributes
    ----------
    method_P : str
        The method was which was last used successfully to calculate a property;
        set only after the first property calculation.
    method : str
        The method to be used for property calculations, [-]
    all_methods : set
        All low-pressure methods available, [-]
    all_methods_P : set
        All pressure-dependent methods available, [-]

    '''

    P_dependent = True
    interpolation_P = None

    P_correlation_models = {
        'Tait': {'custom': True},
    }
    available_P_correlations = frozenset(P_correlation_models.keys())

    P_correlation_parameters = {k: k + '_parameters' for k in P_correlation_models.keys()}
    P_correlation_keys_to_parameters = {v: k for k, v in P_correlation_parameters.items()}

    def __init__(self, extrapolation, **kwargs):
        self.tabular_data_P = {}
        """tabular_data_P, dict: Stored (Ts, Ps, properties) for any
        tabular data; indexed by provided or autogenerated name."""

        self.tabular_data_interpolators_P = {}
        """tabular_data_interpolators_P, dict: Stored (extrapolator,
        spline) tuples which are interp2d instances for each set of tabular
        data; indexed by tuple of (name, interpolation_T, interpolation_P,
        interpolation_property, interpolation_property_inv) to ensure that
        if an interpolation transform is altered, the old interpolator which
        had been created is no longer used."""

        self.P_correlations = {}

        super().__init__(extrapolation, **kwargs)

        self.P_limits = {}
        """Pressure limits on a per-component basis. Not currently used."""

        if kwargs:
            P_correlation_keys_to_parameters = self.P_correlation_keys_to_parameters
            # Iterate over all the dictionaries in reverse such that the first one is left as the default
            for key in reversed(list(kwargs.keys())):
                if key in P_correlation_keys_to_parameters:
                    P_correlation_dict = kwargs.pop(key)
                    P_correlation_name = P_correlation_keys_to_parameters[key]
                    # Probably need to reverse this too
                    for corr_i, corr_kwargs in P_correlation_dict.items():
                        self.add_P_correlation(name=corr_i, model=P_correlation_name,
                                             **corr_kwargs)

        self.tabular_extrapolation_permitted = kwargs.get('tabular_extrapolation_permitted', True)

        if kwargs.get('tabular_data_P', None):
            for name, (Ts, Ps, properties) in kwargs['tabular_data_P'].items():
                self.add_tabular_data_P(Ts, Ps, properties, name=name, check_properties=False)

        method_P = kwargs.get('method_P', getattr(self, '_method_P', None))
        if method_P is None:
            all_methods_P = self.all_methods_P
            for i in self.ranked_methods_P:
                if i in all_methods_P:
                    method_P = i
                    break
        self.method_P = method_P

    def load_all_methods(self, load_data):
        self.all_methods_P = set()
        """Set of all methods available for a given CASRN and properties;
        filled by :obj:`load_all_methods`."""

        self.all_methods = set()
        """Set of all P-dependent methods available for a given CASRN and properties;
        filled by :obj:`load_all_methods`."""

    def add_P_correlation(self, name, model, **kwargs):
        d = getattr(self, model + '_parameters', None)
        if d is None:
            d = {}
            setattr(self, model + '_parameters', d)

        full_kwargs = kwargs.copy()
        d[name] = full_kwargs
        self.all_methods.add(name)
        self.method = name

        args = (kwargs['coeffs'], kwargs['N_terms'], kwargs['N_T'])

        self.P_correlations[name] = args

    @property
    def method_P(self):
        r'''Method used to set or get a specific property method.

        An exception is raised if the method specified isnt't available
        for the chemical with the provided information.

        Parameters
        ----------
        method : str or list
            Methods by name to be considered or preferred
        '''
        return self._method_P

    @method_P.setter
    def method_P(self, method_P):
        if method_P not in self.all_methods_P and method_P is not None:
            raise ValueError("The given methods is not available for this chemical")
        self.TP_cached = None
        self._method_P = method_P

    def __call__(self, T, P):
        r'''Convenience method to calculate the property; calls
        :obj:`TP_dependent_property <thermo.utils.TPDependentProperty.TP_dependent_property>`. Caches previously calculated value,
        which is an overhead when calculating many different values of
        a property. See :obj:`TP_dependent_property <thermo.utils.TPDependentProperty.TP_dependent_property>` for more details as to the
        calculation procedure.

        Parameters
        ----------
        T : float
            Temperature at which to calculate the property, [K]
        P : float
            Pressure at which to calculate the property, [Pa]

        Returns
        -------
        prop : float
            Calculated property, [`units`]
        '''
        if (T, P) == self.TP_cached:
            return self.prop_cached
        else:
            if P is not None:
                self.prop_cached = self.TP_dependent_property(T, P)
            else:
                self.prop_cached = self.T_dependent_property(T)
            self.TP_cached = (T, P)
            return self.prop_cached

    def valid_methods_P(self, T=None, P=None):
        r'''Method to obtain a sorted list of high-pressure methods that have
        data available to be used. The methods are ranked in the following
        order:

        * The currently selected :obj:`method_P` is first (if one is selected)
        * Other available pressure-depenent methods are ranked by the attribute
          :obj:`ranked_methods_P`

        If `T` and `P` are provided, the methods will be checked against the
        temperature and pressure limits of the correlations as well.

        Parameters
        ----------
        T : float
            Temperature at which to test methods, [K]
        P : float
            Pressure at which to test methods, [Pa]

        Returns
        -------
        sorted_valid_methods_P : list
            Sorted lists of methods valid at T and P according to
            :obj:`test_method_validity_P`
        '''
        all_methods = self.all_methods_P
        sorted_methods = [i for i in self.ranked_methods_P if i in all_methods]
        current_method = self._method_P
        if current_method in sorted_methods:
            # Add back the user's methods to the top, in order.
            sorted_methods.remove(current_method)
            sorted_methods.insert(0, current_method)
        if T is not None:
            sorted_methods = [i for i in sorted_methods
                              if self.test_method_validity_P(T, P, i)]
        return sorted_methods

    def TP_dependent_property(self, T, P):
        r'''Method to calculate the property given a temperature and pressure
        according to the selected :obj:`method_P` and :obj:`method`.
        The pressure-dependent method is always used and required to succeed.
        The result is checked with :obj:`test_property_validity`.

        If the method does not succeed, returns None.

        Parameters
        ----------
        T : float
            Temperature at which to calculate the property, [K]
        P : float
            Pressure at which to calculate the property, [Pa]

        Returns
        -------
        prop : float
            Calculated property, [`units`]
        '''
        method_P = self._method_P
        if method_P is None:
            if self.RAISE_PROPERTY_CALCULATION_ERROR:
                raise RuntimeError(f"No pressure-dependent {self.name.lower()} method selected for component with CASRN '{self.CASRN}'")
            else:
                return None
        if self.test_method_validity_P(T, P, method_P):
            try:
                prop = self.calculate_P(T, P, method_P)
            except:  # pragma: no cover
                if self.RAISE_PROPERTY_CALCULATION_ERROR:
                    raise RuntimeError(f"Failed to evaluate {self.name.lower()} method '{method_P}' at T={T} K and P={P} Pa for component with CASRN '{self.CASRN}'")
            else:
                if self.test_property_validity(prop):
                    return prop
                elif self.RAISE_PROPERTY_CALCULATION_ERROR:
                    raise RuntimeError(f"{self.name} method '{method_P}' computed an invalid value of {prop} {self.units} for component with CASRN '{self.CASRN}'")
        elif self.RAISE_PROPERTY_CALCULATION_ERROR:
            raise RuntimeError(f"{self.name} method '{method_P}' is not valid at T={T} K and P={P} Pa for component with CASRN '{self.CASRN}'")

    def TP_or_T_dependent_property(self, T, P):
        r'''Method to calculate the property given a temperature and pressure
        according to the selected :obj:`method_P` and :obj:`method`.
        The pressure-dependent method is always tried.
        The result is checked with :obj:`test_property_validity`.

        If the pressure-dependent method does not succeed, the low-pressure
        method is tried and its result is returned.

        .. warning::
            It can seem like a good idea to switch between a low-pressure and
            a high-pressure method if the high pressure method is not working,
            however it can cause discontinuities and prevent numerical methods
            from converging

        Parameters
        ----------
        T : float
            Temperature at which to calculate the property, [K]
        P : float
            Pressure at which to calculate the property, [Pa]

        Returns
        -------
        prop : float
            Calculated property, [`units`]
        '''
        if P is not None:
            prop = self.TP_dependent_property(T, P)
        if P is None or prop is None:
            prop = self.T_dependent_property(T)
        return prop

    def T_atmospheric_dependent_property(self, T, P_atm=101325.0):
        r'''Method to calculate the property given a temperature at the standard
        atmospheric pressure to the selected :obj:`method_P` and :obj:`method`.
        This is a wrapper around :obj:`TP_dependent_property`.

        Parameters
        ----------
        T : float
            Temperature at which to calculate the property, [K]
        P_atm : float, optional
            Atmospheric pressure at which to calculate the property, [Pa]

        Returns
        -------
        prop : float
            Calculated property, [`units`]
        '''
        return self.TP_dependent_property(T, P_atm)

    def add_tabular_data_P(self, Ts, Ps, properties, name=None, check_properties=True):
        r'''Method to set tabular data to be used for interpolation.
        Ts and Psmust be in increasing order. If no name is given, data will be
        assigned the name 'Tabular data series #x', where x is the number of
        previously added tabular data series.

        After adding the data, this method becomes the selected high-pressure
        method.


        Parameters
        ----------
        Ts : array-like
            Increasing array of temperatures at which properties are specified, [K]
        Ps : array-like
            Increasing array of pressures at which properties are specified, [Pa]
        properties : array-like
            List of properties at `Ts` and `Ps`; the data should be indexed
            [P][T], [`units`]
        name : str, optional
            Name assigned to the data
        check_properties : bool
            If True, the properties will be checked for validity with
            :obj:`test_property_validity` and raise an exception if any are not
            valid
        '''
        # Ts must be in increasing order.
        if check_properties:
            for p in np.array(properties).ravel():
                if not self.test_property_validity(p):
                    raise ValueError('One of the properties specified are not feasible')
        if not all(b > a for a, b in zip(Ts, Ts[1:])):
            raise ValueError('Temperatures are not sorted in increasing order')
        if not all(b > a for a, b in zip(Ps, Ps[1:])):
            raise ValueError('Pressures are not sorted in increasing order')

        if name is None:
            name = 'Tabular data series #' + str(len(self.tabular_data))  # Will overwrite a poorly named series
        self.tabular_data_P[name] = [Ts, Ps, properties]
        self.all_methods_P.add(name)
        self.method_P = name

    def test_method_validity_P(self, T, P, method):
        r'''Method to test the validity of a specified method for a given
        temperature. Demo function for testing only;
        must be implemented according to the methods available for each
        individual method. Include the interpolation check here.

        Parameters
        ----------
        T : float
            Temperature at which to determine the validity of the method, [K]
        P : float
            Pressure at which to determine the validity of the method, [Pa]
        method : str
            Method name to use

        Returns
        -------
        validity : bool
            Whether or not a specifid method is valid
        '''
        if method in self.tabular_data_P:
            if self.tabular_extrapolation_permitted:
                validity = True
            else:
                Ts, Ps, properties = self.tabular_data_P[method]
                validity = Ts[0] < T < Ts[-1] and Ps[0] < P < Ps[-1]
        elif method == NEGLECT_P:
            return self.test_method_validity(T, self._method) if self._method else False
        elif method in self.all_methods_P:
            Tmin, Tmax = self.T_limits[method]
            validity = Tmin < T < Tmax
        else:
            raise ValueError("method '%s' not valid" %method)
        return validity

    def interpolate_P(self, T, P, name):
        r'''Method to perform interpolation on a given tabular data set
        previously added via :obj:`add_tabular_data_P`. This method will create the
        interpolators the first time it is used on a property set, and store
        them for quick future use.

        Interpolation is cubic-spline based if 5 or more points are available,
        and linearly interpolated if not. Extrapolation is always performed
        linearly. This function uses the transforms :obj:`interpolation_T`,
        :obj:`interpolation_P`,
        :obj:`interpolation_property`, and :obj:`interpolation_property_inv` if set. If
        any of these are changed after the interpolators were first created,
        new interpolators are created with the new transforms.
        All interpolation is performed via the `interp2d` function.

        Parameters
        ----------
        T : float
            Temperature at which to interpolate the property, [K]
        T : float
            Pressure at which to interpolate the property, [Pa]
        name : str
            The name assigned to the tabular data set

        Returns
        -------
        prop : float
            Calculated property, [`units`]
        '''
        key = (name, self.interpolation_T, id(self.interpolation_P), id(self.interpolation_property), id(self.interpolation_property_inv))
        Ts, Ps, properties = self.tabular_data_P[name]
        if not self.tabular_extrapolation_permitted:
            if T < Ts[0] or T > Ts[-1] or P < Ps[0] or P > Ps[-1]:
                raise ValueError("Extrapolation not permitted and conditions outside of range")

        # If the interpolator and extrapolator has already been created, load it
        if key in self.tabular_data_interpolators_P:
            extrapolator, spline = self.tabular_data_interpolators_P[key]
        else:
            from scipy.interpolate import interp2d


            if self.interpolation_T:  # Transform ths Ts with interpolation_T if set
                Ts2 = [self.interpolation_T(T2) for T2 in Ts]
            else:
                Ts2 = Ts
            if self.interpolation_P:  # Transform ths Ts with interpolation_T if set
                Ps2 = [self.interpolation_P(P2) for P2 in Ps]
            else:
                Ps2 = Ps
            if self.interpolation_property:  # Transform ths props with interpolation_property if set
                properties2 = [[self.interpolation_property(p) for p in r] for r in properties]
            else:
                properties2 = properties
            # Only allow linear extrapolation, but with whatever transforms are specified
            extrapolator = interp2d(Ts2, Ps2, properties2)  # interpolation if fill value is missing
            # If more than 5 property points, create a spline interpolation
            if len(properties) >= 5:
                spline = interp2d(Ts2, Ps2, properties2, kind='cubic')
            else:
                spline = None
            self.tabular_data_interpolators_P[key] = (extrapolator, spline)

        # Load the stores values, tor checking which interpolation strategy to
        # use.
        Ts, Ps, properties = self.tabular_data_P[name]

        if T < Ts[0] or T > Ts[-1] or not spline or P < Ps[0] or P > Ps[-1]:
            tool = extrapolator
        else:
            tool = spline

        if self.interpolation_T:
            T = self.interpolation_T(T)
        if self.interpolation_P:
            P = self.interpolation_P(P)
        prop = tool(T, P)  # either spline, or linear interpolation

        if self.interpolation_property:
            prop = self.interpolation_property_inv(prop)

        return float(prop)

    def plot_isotherm(self, T, Pmin=None, Pmax=None, methods_P=[], pts=50,
                      only_valid=True, show=True):  # pragma: no cover
        r'''Method to create a plot of the property vs pressure at a specified
        temperature according to either a specified list of methods, or the
        user methods (if set), or all methods. User-selectable number of
        points, and pressure range. If only_valid is set,
        :obj:`test_method_validity_P` will be used to check if each condition in
        the specified range is valid, and :obj:`test_property_validity` will be used
        to test the answer, and the method is allowed to fail; only the valid
        points will be plotted. Otherwise, the result will be calculated and
        displayed as-is. This will not suceed if the method fails.

        Parameters
        ----------
        T : float
            Temperature at which to create the plot, [K]
        Pmin : float
            Minimum pressure, to begin calculating the property, [Pa]
        Pmax : float
            Maximum pressure, to stop calculating the property, [Pa]
        methods_P : list, optional
            List of methods to consider
        pts : int, optional
            A list of points to calculate the property at; if Pmin to Pmax
            covers a wide range of method validities, only a few points may end
            up calculated for a given method so this may need to be large
        only_valid : bool
            If True, only plot successful methods and calculated properties,
            and handle errors; if False, attempt calculation without any
            checking and use methods outside their bounds
        show : bool
            If True, displays the plot; otherwise, returns it
        '''
        # This function cannot be tested
        if not has_matplotlib():
            raise Exception('Optional dependency matplotlib is required for plotting')
        import matplotlib.pyplot as plt
        if Pmin is None:
            if self.Pmin is not None:
                Pmin = self.Pmin
            else:
                raise Exception('Minimum pressure could not be auto-detected; please provide it')
        if Pmax is None:
            if self.Pmax is not None:
                Pmax = self.Pmax
            else:
                raise Exception('Maximum pressure could not be auto-detected; please provide it')
        fig = plt.figure()

        if not methods_P:
            methods_P = self.all_methods_P
        Ps = linspace(Pmin, Pmax, pts)
        for method_P in methods_P:
            if only_valid:
                properties, Ps2 = [], []
                for P in Ps:
                    if self.test_method_validity_P(T, P, method_P):
                        try:
                            p = self.calculate_P(T, P, method_P)
                            if self.test_property_validity(p):
                                properties.append(p)
                                Ps2.append(P)
                        except:
                            pass
                plt.plot(Ps2, properties, label=method_P)
            else:
                properties = [self.calculate_P(T, P, method_P) for P in Ps]
                plt.plot(Ps, properties, label=method_P)
        plt.legend(loc='best')
        plt.ylabel(self.name + ', ' + self.units)
        plt.xlabel('Pressure, Pa')
        plt.title(self.name + ' of ' + self.CASRN)
        if show:
            plt.show()
        else:
            return plt

    def plot_isobar(self, P, Tmin=None, Tmax=None, methods_P=[], pts=50,
                    only_valid=True, show=True):  # pragma: no cover
        r'''Method to create a plot of the property vs temperature at a
        specific pressure according to
        either a specified list of methods, or user methods (if set), or all
        methods. User-selectable number of points, and temperature range. If
        only_valid is set,:obj:`test_method_validity_P` will be used to check if
        each condition in the specified range is valid, and
        :obj:`test_property_validity` will be used to test the answer, and the
        method is allowed to fail; only the valid points will be plotted.
        Otherwise, the result will be calculated and displayed as-is. This will
        not suceed if the method fails.

        Parameters
        ----------
        P : float
            Pressure for the isobar, [Pa]
        Tmin : float
            Minimum temperature, to begin calculating the property, [K]
        Tmax : float
            Maximum temperature, to stop calculating the property, [K]
        methods_P : list, optional
            List of methods to consider
        pts : int, optional
            A list of points to calculate the property at; if Tmin to Tmax
            covers a wide range of method validities, only a few points may end
            up calculated for a given method so this may need to be large
        only_valid : bool
            If True, only plot successful methods and calculated properties,
            and handle errors; if False, attempt calculation without any
            checking and use methods outside their bounds
        '''
        if not has_matplotlib():
            raise Exception('Optional dependency matplotlib is required for plotting')
        import matplotlib.pyplot as plt
        if Tmin is None:
            if self._T_min_any is not None:
                Tmin = self._T_min_any
            else:
                raise Exception('Minimum temperature could not be auto-detected; please provide it')
        if Tmax is None:
            if self._T_max_any is not None:
                Tmax = self._T_max_any
            else:
                raise Exception('Maximum temperature could not be auto-detected; please provide it')
        if hasattr(P, '__call__'):
            P_changes = True
            P_func = P
        else:
            P_changes = False
        if not methods_P:
            methods_P = self.all_methods_P
        Ts = linspace(Tmin, Tmax, pts)
        fig = plt.figure()
        for method_P in methods_P:
            if only_valid:
                properties, Ts2 = [], []
                for T in Ts:
                    if P_changes:
                        P = P_func(T)
                    if self.test_method_validity_P(T, P, method_P):
                        try:
                            p = self.calculate_P(T, P, method_P)
                            if self.test_property_validity(p):
                                properties.append(p)
                                Ts2.append(T)
                        except:
                            pass
                plt.plot(Ts2, properties, label=method_P)
            else:
                properties = []
                for T in Ts:
                    if P_changes:
                        P = P_func(T)
                properties.append(self.calculate_P(T, P, method_P))

                plt.plot(Ts, properties, label=method_P)
        plt.legend(loc='best')
        plt.ylabel(self.name + ', ' + self.units)
        plt.xlabel('Temperature, K')
        plt.title(self.name + ' of ' + self.CASRN)
        if show:
            plt.show()
        else:
            return plt


    def plot_TP_dependent_property(self, Tmin=None, Tmax=None, Pmin=None,
                                   Pmax=None,  methods_P=[], pts=15,
                                   only_valid=True):  # pragma: no cover
        r'''Method to create a plot of the property vs temperature and pressure
        according to either a specified list of methods, or user methods (if
        set), or all methods. User-selectable number of points for each
        variable. If only_valid is set,:obj:`test_method_validity_P` will be used to
        check if each condition in the specified range is valid, and
        :obj:`test_property_validity` will be used to test the answer, and the
        method is allowed to fail; only the valid points will be plotted.
        Otherwise, the result will be calculated and displayed as-is. This will
        not suceed if the any method fails for any point.

        Parameters
        ----------
        Tmin : float
            Minimum temperature, to begin calculating the property, [K]
        Tmax : float
            Maximum temperature, to stop calculating the property, [K]
        Pmin : float
            Minimum pressure, to begin calculating the property, [Pa]
        Pmax : float
            Maximum pressure, to stop calculating the property, [Pa]
        methods_P : list, optional
            List of methods to plot
        pts : int, optional
            A list of points to calculate the property at for both temperature
            and pressure; pts^2 points will be calculated.
        only_valid : bool
            If True, only plot successful methods and calculated properties,
            and handle errors; if False, attempt calculation without any
            checking and use methods outside their bounds
        '''
        if not has_matplotlib():
            raise Exception('Optional dependency matplotlib is required for plotting')
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FormatStrFormatter
        from numpy import ma

        if Pmin is None:
            if self.Pmin is not None:
                Pmin = self.Pmin
            else:
                raise Exception('Minimum pressure could not be auto-detected; please provide it')
        if Pmax is None:
            if self.Pmax is not None:
                Pmax = self.Pmax
            else:
                raise Exception('Maximum pressure could not be auto-detected; please provide it')
        if Tmin is None:
            if self._T_min_any is not None:
                Tmin = self._T_min_any
            else:
                raise Exception('Minimum temperature could not be auto-detected; please provide it')
        if Tmax is None:
            if self._T_max_any is not None:
                Tmax = self._T_max_any
            else:
                raise Exception('Maximum temperature could not be auto-detected; please provide it')

        if not methods_P:
            methods_P = self.all_methods_P
        Ps = np.linspace(Pmin, Pmax, pts)
        Ts = np.linspace(Tmin, Tmax, pts)
        Ts_mesh, Ps_mesh = np.meshgrid(Ts, Ps)
        fig = plt.figure()
        ax = fig.add_subplot(1,1,1,projection="3d")

        handles = []
        for method_P in methods_P:
            if only_valid:
                properties = []
                for T in Ts:
                    T_props = []
                    for P in Ps:
                        if self.test_method_validity_P(T, P, method_P):
                            try:
                                p = self.calculate_P(T, P, method_P)
                                if self.test_property_validity(p):
                                    T_props.append(p)
                                else:
                                    T_props.append(None)
                            except:
                                T_props.append(None)
                        else:
                            T_props.append(None)
                    properties.append(T_props)
                properties = ma.masked_invalid(np.array(properties, dtype=np.float64).T)
                handles.append(ax.plot_surface(Ts_mesh, Ps_mesh, properties, cstride=1, rstride=1, alpha=0.5))
            else:
                properties = np.array([[self.calculate_P(T, P, method_P) for T in Ts] for P in Ps])
                handles.append(ax.plot_surface(Ts_mesh, Ps_mesh, properties, cstride=1, rstride=1, alpha=0.5))

        ax.yaxis.set_major_formatter(FormatStrFormatter('%.4g'))
        ax.zaxis.set_major_formatter(FormatStrFormatter('%.4g'))
        ax.xaxis.set_major_formatter(FormatStrFormatter('%.4g'))
        ax.set_xlabel('Temperature, K')
        ax.set_ylabel('Pressure, Pa')
        ax.set_zlabel(self.name + ', ' + self.units)
        plt.title(self.name + ' of ' + self.CASRN)
        plt.show(block=False)

    def calculate_derivative_T(self, T, P, method, order=1):
        r'''Method to calculate a derivative of a temperature and pressure
        dependent property with respect to  temperature at constant pressure,
        of a given order using a specified  method. Uses SciPy's  derivative
        function, with a delta of 1E-6 K and a number of points equal to
        2*order + 1.

        This method can be overwritten by subclasses who may perfer to add
        analytical methods for some or all methods as this is much faster.

        If the calculation does not succeed, returns the actual error
        encountered.

        Parameters
        ----------
        T : float
            Temperature at which to calculate the derivative, [K]
        P : float
            Pressure at which to calculate the derivative, [Pa]
        method : str
            Method for which to find the derivative
        order : int
            Order of the derivative, >= 1

        Returns
        -------
        dprop_dT_P : float
            Calculated derivative property at constant pressure,
            [`units/K^order`]
        '''
        return derivative(self.calculate_P, T, dx=1e-6, args=[P, method], n=order, order=1+order*2)

    def calculate_derivative_P(self, P, T, method, order=1):
        r'''Method to calculate a derivative of a temperature and pressure
        dependent property with respect to pressure at constant temperature,
        of a given order using a specified method. Uses SciPy's derivative
        function, with a delta of 0.01 Pa and a number of points equal to
        2*order + 1.

        This method can be overwritten by subclasses who may perfer to add
        analytical methods for some or all methods as this is much faster.

        If the calculation does not succeed, returns the actual error
        encountered.

        Parameters
        ----------
        P : float
            Pressure at which to calculate the derivative, [Pa]
        T : float
            Temperature at which to calculate the derivative, [K]
        method : str
            Method for which to find the derivative
        order : int
            Order of the derivative, >= 1

        Returns
        -------
        dprop_dP_T : float
            Calculated derivative property at constant temperature,
            [`units/Pa^order`]
        '''
        f = lambda P: self.calculate_P(T, P, method)
        return derivative(f, P, dx=1e-2, n=order, order=1+order*2)

    def TP_dependent_property_derivative_T(self, T, P, order=1):
        r'''Method to calculate a derivative of a temperature and pressure
        dependent property with respect to temperature at constant pressure,
        of a given order, according to the selected :obj:`method_P`.

        Calls :obj:`calculate_derivative_T` internally to perform the actual
        calculation.

        .. math::
            \text{derivative} = \frac{d (\text{property})}{d T}|_{P}

        Parameters
        ----------
        T : float
            Temperature at which to calculate the derivative, [K]
        P : float
            Pressure at which to calculate the derivative, [Pa]
        order : int
            Order of the derivative, >= 1

        Returns
        -------
        dprop_dT_P : float
            Calculated derivative property, [`units/K^order`]
        '''
        try:
            return self.calculate_derivative_T(T, P, self._method_P, order)
        except:
            pass
        return None

    def TP_dependent_property_derivative_P(self, T, P, order=1):
        r'''Method to calculate a derivative of a temperature and pressure
        dependent property with respect to pressure at constant temperature,
        of a given order, according to the selected :obj:`method_P`.

        Calls :obj:`calculate_derivative_P` internally to perform the actual
        calculation.

        .. math::
            \text{derivative} = \frac{d (\text{property})}{d P}|_{T}

        Parameters
        ----------
        T : float
            Temperature at which to calculate the derivative, [K]
        P : float
            Pressure at which to calculate the derivative, [Pa]
        order : int
            Order of the derivative, >= 1

        Returns
        -------
        dprop_dP_T : float
            Calculated derivative property, [`units/Pa^order`]
        '''
        try:
            return self.calculate_derivative_P(P, T, self._method_P, order)
        except:
            pass
        return None

