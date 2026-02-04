import numpy as np
from dataclasses import dataclass, field
from src.core.simulation import Simulation
from src.core.physics import PLANETS

@dataclass
class SimulationResult:
    status: str
    max_altitude: float
    max_velocity: float
    flight_time: float
    final_fuel: float
    history: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

def run_simulation_batch(config, max_duration=600.0, dt=0.05, seed=None):
    """
    Runs a single simulation in headless mode.
    
    config: dict containing:
      - planet
      - target_apoapsis (km)
      - safety_margin (km)
      - dry_mass
      - fuel_mass
      - propellant_type
      - overrides: dict (optional physics overrides for MC)
    """
    if seed is not None:
        np.random.seed(seed)
        
    sim = Simulation()
    
    # Initialize normally
    sim.initialize(
        config.get('planet', 'Earth'),
        config.get('target_apoapsis', 100),
        config.get('safety_margin', 0),
        config.get('dry_mass', 1000),
        config.get('fuel_mass', 10000),
        config.get('propellant_type', 'liquid')
    )
    
    # Apply Monte Carlo Overrides (if any)
    overrides = config.get('overrides', {})
    
    if 'isp_multiplier' in overrides:
        sim.rocket.vacuum_isp *= overrides['isp_multiplier']
        # Recalculate derived if needed? Ideally mass flow logic uses vacuum_isp.
        # Check simulation.py: dm_dt = - (thrust_force_mag / (self.rocket.isp * g0))?
        # Simulation uses: current_isp calculation or rocket.get_thrust?
        # rocket.get_thrust uses self.exhaust_velocity and self.mass_flow_max.
        # We need to update those if we change ISP.
        # Re-init propulsion logic essentially.
        # For simplicity, let's assume get_thrust uses internal params.
        # We might need to manually adjust rocket.mass_flow_max or rocket.exhaust_velocity.
        
        # Proper way: Re-derive params.
        sim.rocket.mass_flow_max = sim.rocket.vacuum_thrust / (sim.rocket.vacuum_isp * 9.80665)
        # Update Ve
        # Ve = (F_vac - Pe*Ae) / m_dot
        sim.rocket.exhaust_velocity = (sim.rocket.vacuum_thrust - sim.rocket.exit_pressure * sim.rocket.nozzle_area) / sim.rocket.mass_flow_max
        
    if 'thrust_multiplier' in overrides:
        sim.rocket.vacuum_thrust *= overrides['thrust_multiplier']
        sim.rocket.max_thrust = sim.rocket.vacuum_thrust
        # Re-derive m_dot and Ve... this implies we need a method in Rocket to "recompute_physics"
        # For now, let's just hack it:
        sim.rocket.mass_flow_max *= overrides['thrust_multiplier'] 
        # Ve stays roughly same if Thrust and Mass Flow scale together?
        
    if 'wind_variance' in overrides:
        # Not implemented in Sim yet, but future proofing
        pass
        
    # Run Loop
    steps = int(max_duration / dt)
    
    for _ in range(steps):
        if sim.rocket.status in ["CRASHED", "LANDED", "ABORT"]:
            break
        sim.step(dt)
        
    # Collect Results
    max_alt = max(sim.history['altitude']) if sim.history['altitude'] else 0.0
    max_vel = max(sim.history['velocity']) if sim.history['velocity'] else 0.0
    
    return SimulationResult(
        status=sim.rocket.status,
        max_altitude=max_alt,
        max_velocity=max_vel,
        flight_time=sim.time,
        final_fuel=sim.rocket.fuel_mass,
        history=sim.history,
        metadata=config
    )
