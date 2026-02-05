import argparse
import random
import os
import sys
import json
import csv
import matplotlib
matplotlib.use('Agg') # Headless plotting
import matplotlib.pyplot as plt
import numpy as np

# Add project root to path to import src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.core.simulation import Simulation

PLANETS = ['Earth', 'Moon', 'Mars', 'Mercury', 'Venus', 'Pluto']

def generate_config(planet_name):
    """Generates random mission parameters."""
    return {
        'planet': planet_name,
        'target_apoapsis': round(random.uniform(50, 300), 2), # km
        'safety_margin': round(random.uniform(5, 50), 2), # km
        'propellant': random.choice(['solid', 'liquid']),
        'dry_mass': round(random.uniform(100, 2000), 2), # kg
        'fuel_mass': round(random.uniform(200, 500000), 2) # kg
    }

def run_simulation_headless(config, output_dir):
    """Runs a single simulation and saves results."""
    sim = Simulation()
    sim.initialize(
        config['planet'],
        config['target_apoapsis'],
        config['safety_margin'],
        config['dry_mass'],
        config['fuel_mass'],
        config['propellant']
    )
    
    # Check Feasibility
    is_feasible, rejection_reason, dv, req_dv, extra = sim.check_feasibility(
        config['planet'], 
        config['target_apoapsis'], 
        config['dry_mass'], 
        config['fuel_mass'], 
        config['propellant'],
        config['safety_margin']
    )
    
    if not is_feasible:
        print(f" (REJECTED: {rejection_reason}) ", end="")
        return {
            'status': "REJECTED",
            'outcome': f"REJECTED ({rejection_reason})",
            'max_altitude_m': 0, 'max_velocity_ms': 0, 'max_q_pa': 0, 'flight_time_s': 0,
            'fuel_remaining_kg': 0, 'achieved_apoapsis_km': 0,
            'feasibility': rejection_reason
        }

    # Run Loop
    max_time = 20000.0 # Increased timeout for Mars/Moon (lower gravity = longer flight)
    dt = 0.05
    
    # Data collection
    times = []
    alts = []
    vels = []
    downranges = []
    status_history = []
    
    # Max Q tracking
    max_q = 0.0
    
    while sim.time < max_time:
        sim.step(dt)
        
        # Collect Data
        times.append(sim.time)
        state = sim.rocket
        pos_mag = np.linalg.norm(state.position)
        alt = pos_mag - sim.planet.radius
        vel_mag = np.linalg.norm(state.velocity)
        
        # Downrange (Simple arc length approximation)
        # initial pos is (0, R). current is (x, y).
        # angle = atan2(x, y). downrange = angle * R
        angle = np.arctan2(state.position[0], state.position[1])
        downrange = angle * sim.planet.radius
        
        alts.append(alt)
        vels.append(vel_mag)
        downranges.append(downrange)
        status_history.append(state.status)
        
        rho = sim.planet.atmosphere_density(alt)
        q = 0.5 * rho * vel_mag**2
        max_q = max(max_q, q)

            
        if state.status in ["CRASHED", "LANDED", "ABORT"]:
            break
            
    # Metrics
    success = (
        sim.rocket.max_apoapsis_km >= config['target_apoapsis'] - config['safety_margin']
        and sim.rocket.status not in ["CRASHED", "ABORT"]
    )
 # Or just reaching orbit?
    # User said "successful and failure scenarios". 
    # Usually success means reaching target apoapsis? 
    # Or simplified: Did it crash?
    
    # Calculate achieved apoapsis
    achieved_apo = max(alts) if alts else 0.0
    
    # Determine Final Outcome
    # This sets sim.mission_outcome field
    outcome = sim.determine_outcome()
    
    metrics = {
        'status': sim.rocket.status,
        'outcome': outcome, # SUCCESS, FAILED, ABORTED
        'max_altitude_m': round(max(alts), 2) if alts else 0,
        'max_velocity_ms': round(max(vels), 2) if vels else 0,
        'max_q_pa': round(max_q, 2),
        'flight_time_s': round(sim.time, 2),
        'fuel_remaining_kg': round(sim.rocket.fuel_mass, 2),
        'achieved_apoapsis_km': round(achieved_apo / 1000.0, 2),
        'feasibility': "OK"
    }
    
    # === Logging ===
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Config JSON
    with open(os.path.join(output_dir, "mission_config.json"), "w") as f:
        json.dump(config, f, indent=4)
        
    # 2. Text Log
    with open(os.path.join(output_dir, "mission_log.txt"), "w") as f:
        f.write("MISSION LOG\n")
        f.write("===========\n")
        for k, v in config.items():
            f.write(f"{k}: {v}\n")
        f.write("-" * 20 + "\n")
        f.write(f"Final Status: {metrics['status']}\n")
        f.write(f"Outcome: {metrics['outcome']}\n")
        f.write(f"Flight Time: {metrics['flight_time_s']} s\n")
        f.write(f"Max Altitude: {metrics['max_altitude_m']:.2f} m\n")
        f.write(f"Achieved Apoapsis: {metrics['achieved_apoapsis_km']} km\n")
        f.write(f"Max Q: {metrics['max_q_pa']} Pa\n")
        f.write(f"Fuel Remaining: {metrics['fuel_remaining_kg']} kg\n")

    # 3. Plots
    # Alt vs Time
    plt.figure()
    plt.plot(times, alts)
    plt.title(f"Altitude vs Time ({config['planet']})")
    plt.xlabel("Time (s)")
    plt.ylabel("Altitude (m)")
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "altitude_vs_time.png"))
    plt.close()
    
    # Vel vs Time
    plt.figure()
    plt.plot(times, vels)
    plt.title(f"Velocity vs Time ({config['planet']})")
    plt.xlabel("Time (s)")
    plt.ylabel("Velocity (m/s)")
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "velocity_vs_time.png"))
    plt.close()
    
    # Downrange vs Altitude
    plt.figure()
    plt.plot(downranges, alts)
    plt.title(f"Altitude vs Downrange ({config['planet']})")
    plt.xlabel("Downrange (m)")
    plt.ylabel("Altitude (m)")
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "downrange_vs_altitude.png"))
    plt.close()
    
    return metrics

def run_tests_for_planet(planet_name, base_output_dir):
    results = []
    print(f"Running tests for {planet_name}...")
    
    planet_dir = os.path.join(base_output_dir, planet_name)
    
    for i in range(1, 6): # 5 Tests
        test_name = f"Test_{i}"
        test_dir = os.path.join(planet_dir, test_name)
        print(f"  > Running {test_name}...", end="", flush=True)
        
        config = generate_config(planet_name)
        metrics = run_simulation_headless(config, test_dir)
        
        # Combine config + metrics for summary
        row = {**config, **metrics, 'test_id': f"{planet_name}_{test_name}"}
        results.append(row)
        print(f" Done ({metrics['status']})")
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Run random rocket simulations.")
    parser.add_argument("--count", type=int, default=10, help="Number of simulations to run")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--planet", type=str, default=None, help="Force specific planet")
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
        print(f"Random Seed: {args.seed}")
        
    base_output_dir = os.path.join(project_root, "tests", "random_results")
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir)

    all_results = []
    
    # Generate batch
    for i in range(args.count):
        # Pick random planet if not specified
        p = args.planet if args.planet else random.choice(PLANETS)
        test_id = f"Run_{i+1:03d}_{p}"
        test_dir = os.path.join(base_output_dir, test_id)
        
        print(f"Running {test_id}...", end="", flush=True)
        config = generate_config(p)
        metrics = run_simulation_headless(config, test_dir)
        
        row = {**config, **metrics, 'run_id': test_id, 'planet': p}
        all_results.append(row)
        print(f" Done ({metrics['outcome']})")

    # Write Summary CSV
    if all_results:
        csv_path = os.path.join(base_output_dir, "summary.csv")
        # Fieldnames: run_id, planet, ... config keys ... metrics keys
        # We know specific keys we want? Or just all?
        # User requested: outcome, failure cause, feasibility flags.
        # Let's dump everything for detail.
        keys = list(all_results[0].keys())
        # Ensure outcome and feasibility are there.
        
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_results)
            
        print(f"\nSummary saved to: {csv_path}")
        
        # Stats
        outcomes = [r['outcome'].split(' ')[0] for r in all_results]
        from collections import Counter
        print(f"Outcomes: {Counter(outcomes)}")

if __name__ == "__main__":
    main()
