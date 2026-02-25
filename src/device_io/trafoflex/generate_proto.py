"""
Functions that configure Trafoflex simulation requests.
"""

def configure_request_base(request):
    """Configure the simulation request parameters that aren't measurement inputs or transformer model"""

    # Numerical setup
    request.numerical_setup.time_step = 30
    request.numerical_setup.max_change = 1
    request.numerical_setup.debug_level = 0
    request.numerical_setup.training_mode = True
    request.numerical_setup.bisection_accuracy = 1
    request.numerical_setup.bisection_max_iter = 10
    request.numerical_setup.bisection_min_current = 1
    request.numerical_setup.steady_state_crit = 1e-10
    request.numerical_setup.steady_state_max_time = 1500000
    request.output_folder = "simulation_output"


def configure_test_request(request):
    """A configuration function intended to be used in code testing to check for result reproducibility.
    If this is changed, tests may fail."""
    # Copy of parameters from the 6001-TP_ŽELEZNO transformer model.
    tm = request.transformer_model
    tm.internal_state.time = 0.
    tm.internal_state.internal_mass_temperatures.append(10.5)
    tm.internal_state.internal_mass_temperatures.append(10.5)
    
    coeff = tm.coeff.add()
    coeff.joule_heating.I_n = 220.
    coeff.joule_heating.P_0 = 294.
    coeff.joule_heating.P_n = 2419.
    coeff.natural_convection.k_1 = 833.9457528554221
    coeff.natural_convection.k_2 = 0.5000000002876218
    coeff.tau = 196500.61265839988

    coeff = tm.coeff.add()
    coeff.natural_convection.k_1 = 1.9247154919192522
    coeff.natural_convection.k_2 = 2.0
    coeff.radiation.k_1 = 3.8952507859097665
    coeff.tau = 493974.8146785556

    tm.oil_index = 1

    hsm = tm.hot_spot_model
    hsm.winding_time_constant = 240.0
    hsm.winding_exponent = 1.6
    hsm.reference_gradient = 18.0
    
    tm.critical_temperature = 118.0
    tm.critical_part = "hot_spot"
    # End of transformer model.

    # Numerical setup.
    ns = request.numerical_setup
    ns.training_mode = True
    ns.time_step = 30
    ns.max_change = 3.0
    ns.debug_level = 0
    ns.bisection_accuracy = 1.0
    ns.bisection_max_iter = 10
    ns.bisection_min_current = 1.0
    ns.steady_state_crit = 1e-10
    ns.steady_state_max_time = 1500000
    # End of numerical setup.

    # Add a starting measurement.
    mp = request.measurements.add()
    mp.time = 0
    mp.ambient_temperature = 25
    mp.droplet_temperature = 25
    mp.wind_velocity = 0
    mp.wind_angle = 90
    mp.pressure = 105000
    mp.rain_rate = 0
    mp.humidity = 0
    mp.solar_irradiance = 800
    mp.electrical_current = 100

    # Add a final measurement
    mp = request.measurements.add()
    mp.time = 86400 * 3  # 3 days
    mp.ambient_temperature = 25
    mp.droplet_temperature = 25
    mp.wind_velocity = 0
    mp.wind_angle = 90
    mp.pressure = 105000
    mp.rain_rate = 0
    mp.humidity = 0
    mp.solar_irradiance = 800
    mp.electrical_current = 100
    # End of measurements.

def configure_request(request):
    configure_request_base(request)