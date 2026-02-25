"""
Functions that configure Dythera simulation requests.
"""
import device_io.dythera.pb2 as pb

def configure_request_base(request):
    """Configure the request parameters that aren't measurement inputs"""
    request.current_computation_mode = pb.SimulationRequest.CurrentComputationMode.CIGRE_MODEL  # Options: CIGRE_MODEL, RADIAL_MODEL
    request.output_folder = "simulation_out"

    # Nonlinear solver parameteres
    rns = request.nonlinear_solver_parameters
    rns.min_current = 0
    rns.max_current = 5000
    rns.temperature_precision = 0.0001
    rns.current_precision = 0.1
    rns.max_iterations = 30
    rns.debug_level = 1
    
        # Inner simulation setup
    rns.inner_simulation_setup.duration = 10000
    rns.inner_simulation_setup.debug_level = 3

    # Time to overheat setup
    request.time_to_overheat_setup.duration = 6000
    request.time_to_overheat_setup.debug_level = 3

    # Parameters
    #   Line properties
    #     Outer material
    lp = request.parameters.line_properties
    lp.outer_material.density = 2703
    lp.outer_material.specific_heat = 897
    lp.outer_material.specific_heat_alpha = 0.00038
    lp.outer_material.resistivity_alpha = 0.00403
    lp.outer_material.electric_conductivity = 35400000
    lp.outer_material.area = 0.0002431
    lp.outer_material.radius = 0.0109
    lp.outer_material.porosity = 0.75384
    #     Inner material
    lp.inner_material.density = 7780
    lp.inner_material.specific_heat = 481
    lp.inner_material.specific_heat_alpha = 0.0001
    lp.inner_material.resistivity_alpha = 0.0045
    lp.inner_material.electric_conductivity = 1450000
    lp.inner_material.area = 3.95e-05
    lp.inner_material.radius = 0.00402
    lp.inner_material.porosity = 0.77803
    #   Line properties
    lp.line_altitude = 150
    lp.line_angle = 0
    lp.thermal_conductivity = 2
    lp.num_outer_strands = -1
    lp.single_strand_radius = 0.001725
    lp.wetted_factor = 1
    lp.impinging_factor = 1
    lp.recovery_factor = 0.79
    lp.skin_effect = 1.0
    lp.emissivity = 0.7
    lp.absorptivity = 0.7
    lp.rough_surface_correction = 1
    lp.maximal_temperature = 80
    lp.thermal_current_def = pb.LineProperties.ThermalCurrentTemperatureDef.SKIN  # Options: SKIN, CORE, AVG
    lp.nusselt_base.append(0.641)
    lp.nusselt_base.append(0.641)
    lp.nusselt_base.append(0.048)
    lp.nusselt_exponent.append(0.471)
    lp.nusselt_exponent.append(0.471)
    lp.nusselt_exponent.append(0.8) 
    lp.convection_model = pb.LineProperties.ConvectionModel.CIGRE  # Options: CIGRE, IEEE
   
    #   Numerical setup
    rpn = request.parameters.numerical_setup
    rpn.num_nodes = 50
    rpn.time_step = 30
    rpn.steady_state_crit = 1e-07
    rpn.radial_distribution = 0
    rpn.output_rate = 1000000
    rpn.debug_level = 0
    rpn.presimulation_time = 0
    rpn.end_time = 5000
    rpn.initial_skin_temperature = 0
    rpn.initial_electrical_current = 0
    #   Constants of nature
    rpc = request.parameters.constants_of_nature
    rpc.water.density = 1000
    rpc.water.latent_heat_fusion = 336000
    rpc.water.latent_heat_evaporation = 2500000
    rpc.water.latent_heat_sublimation = 2834000
    rpc.water.specific_heat_ice = 2050
    rpc.water.specific_heat_water = 4210
    rpc.air.specific_heat = 1005
    rpc.stefan_constant = 5.67e-08
    rpc.molar_mass_ratio = 0.62
    rpc.gas_constant = 461
    rpc.kelvin_celsius_diff = 273.15


def configure_request(request):
    configure_request_base(request)


def dythera_IEEE_params(request):
    """Generates the IEEE standard test for Dythera. Is used in tests, so changes to this function might make
    tests fail."""
    request.current_computation_mode = pb.SimulationRequest.CurrentComputationMode.CIGRE_MODEL  # Options: CIGRE_MODEL, RADIAL_MODEL
    request.output_folder = "simulation_out"

    # Nonlinear solver parameteres
    rns = request.nonlinear_solver_parameters
    rns.min_current = 0
    rns.max_current = 5000
    rns.temperature_precision = 0.0001
    rns.current_precision = 0.1
    rns.max_iterations = 30
    rns.debug_level = 1
    
        # Inner simulation setup
    rns.inner_simulation_setup.duration = 10000
    rns.inner_simulation_setup.debug_level = 3

    # Time to overheat setup
    request.time_to_overheat_setup.duration = 6000
    request.time_to_overheat_setup.debug_level = 3

    # Parameters
    #   Line properties
    #     Outer material
    lp = request.parameters.line_properties
    lp.outer_material.density = 2703
    lp.outer_material.specific_heat = 897
    lp.outer_material.specific_heat_alpha = 0.00038
    lp.outer_material.resistivity_alpha = 0.00403
    lp.outer_material.electric_conductivity = 35400000
    lp.outer_material.area = 0.0002431
    lp.outer_material.radius = 0.0109
    lp.outer_material.porosity = 0.75384
    #     Inner material
    lp.inner_material.density = 7780
    lp.inner_material.specific_heat = 481
    lp.inner_material.specific_heat_alpha = 0.0001
    lp.inner_material.resistivity_alpha = 0.0045
    lp.inner_material.electric_conductivity = 1450000
    lp.inner_material.area = 3.95e-05
    lp.inner_material.radius = 0.00402
    lp.inner_material.porosity = 0.77803
    #   Line properties
    lp.line_altitude = 150
    lp.line_angle = 0
    lp.thermal_conductivity = 2
    lp.num_outer_strands = -1
    lp.single_strand_radius = 0.001725
    lp.wetted_factor = 1
    lp.impinging_factor = 1
    lp.recovery_factor = 0.79
    lp.skin_effect = 1.0
    lp.emissivity = 0.7
    lp.absorptivity = 0.7
    lp.rough_surface_correction = 1
    lp.maximal_temperature = 80
    lp.thermal_current_def = pb.LineProperties.ThermalCurrentTemperatureDef.SKIN  # Options: SKIN, CORE, AVG
    lp.nusselt_base.append(0.641)
    lp.nusselt_base.append(0.641)
    lp.nusselt_base.append(0.048)
    lp.nusselt_exponent.append(0.471)
    lp.nusselt_exponent.append(0.471)
    lp.nusselt_exponent.append(0.8) 
    lp.convection_model = pb.LineProperties.ConvectionModel.CIGRE  # Options: CIGRE, IEEE
   
    #   Numerical setup
    rpn = request.parameters.numerical_setup
    rpn.num_nodes = 50
    rpn.time_step = 30
    rpn.steady_state_crit = 1e-07
    rpn.radial_distribution = 0
    rpn.output_rate = 1000000
    rpn.debug_level = 0
    rpn.presimulation_time = 0
    rpn.end_time = 5000
    rpn.initial_skin_temperature = 0
    rpn.initial_electrical_current = 0
    #   Constants of nature
    rpc = request.parameters.constants_of_nature
    rpc.water.density = 1000
    rpc.water.latent_heat_fusion = 336000
    rpc.water.latent_heat_evaporation = 2500000
    rpc.water.latent_heat_sublimation = 2834000
    rpc.water.specific_heat_ice = 2050
    rpc.water.specific_heat_water = 4210
    rpc.air.specific_heat = 1005
    rpc.stefan_constant = 5.67e-08
    rpc.molar_mass_ratio = 0.62
    rpc.gas_constant = 461
    rpc.kelvin_celsius_diff = 273.15

    measurement = request.parameters.measurements.add()
    measurement.time = 0.
    measurement.ambient_temperature = 30.
    measurement.droplet_temperature = 30.
    measurement.wind_velocity = 0.
    measurement.wind_angle = 90.
    measurement.pressure = 105000.
    measurement.rain_rate = 0.
    measurement.humidity = 0.
    measurement.solar_irradiance = 900.
    measurement.electrical_current = 480.


if __name__ == "__main__":
    pass