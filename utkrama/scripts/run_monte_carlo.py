import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from src.core.batch_runner import run_simulation_batch
from src.core.logger import SimulationLogger

def run_monte_carlo(args):
    print(f"Running Monte Carlo Simulation ({args.runs} runs)...")
    results = []
    
    base_config = {
        'planet': args.planet,
        'target_apoapsis': args.target_apo,
        'safety_margin': 0,
        'dry_mass': args.dry_mass,
        'fuel_mass': args.fuel_mass,
        'propellant_type': args.propellant
    }
    
    output_dir = f"results/mc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)
    
    stats = {
        'max_alt': [],
        'max_vel': [],
        'status': []
    }
    
    for i in range(args.runs):
        # Generate Random Overrides
        overrides = {}
        if args.noise > 0:
            # +/- noise% variation
            noise_scale = args.noise / 100.0
            overrides['isp_multiplier'] = 1.0 + np.random.uniform(-noise_scale, noise_scale)
            overrides['thrust_multiplier'] = 1.0 + np.random.uniform(-noise_scale, noise_scale)
            
        config = base_config.copy()
        config['overrides'] = overrides
        config['run_id'] = i
        
        res = run_simulation_batch(config, seed=i)
        
        stats['max_alt'].append(res.max_altitude)
        stats['max_vel'].append(res.max_velocity)
        stats['status'].append(res.status)
        
        # Save individual run logs if requested (decimated)
        if args.save_logs:
            SimulationLogger.export_to_csv(res.history, f"{output_dir}/run_{i:03d}.csv")
            
        print(f"Run {i+1}/{args.runs}: {res.status}, Alt={res.max_altitude/1000:.1f}km, Noise_ISP={overrides.get('isp_multiplier', 1.0):.3f}")
        
    # Analysis
    success_rate = stats['status'].count('LANDED') / args.runs * 100.0
    print("\n--- Monte Carlo Results ---")
    print(f"Total Runs: {args.runs}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Mean Max Alt: {np.mean(stats['max_alt'])/1000:.1f} km (Std: {np.std(stats['max_alt'])/1000:.1f} km)")
    
    # Plot Histograms
    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    plt.hist(np.array(stats['max_alt'])/1000, bins=20, color='skyblue', edgecolor='black')
    plt.title("Max Altitude Distribution")
    plt.xlabel("Altitude (km)")
    
    plt.subplot(1, 2, 2)
    plt.hist(np.array(stats['max_vel']), bins=20, color='salmon', edgecolor='black')
    plt.title("Max Velocity Distribution")
    plt.xlabel("Velocity (m/s)")
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/mc_distribution.png")
    print(f"Results saved to {output_dir}")

def run_parameter_sweep(args):
    print(f"Running Parameter Sweep: {args.sweep_param} from {args.sweep_min} to {args.sweep_max}...")
    
    values = np.linspace(args.sweep_min, args.sweep_max, args.sweep_steps)
    results_alt = []
    
    output_dir = f"results/sweep_{args.sweep_param}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)
    
    for val in values:
        config = {
            'planet': args.planet,
            'target_apoapsis': args.target_apo,
            'dry_mass': args.dry_mass,
            'fuel_mass': args.fuel_mass,
            'propellant_type': args.propellant
        }
        
        # Apply sweep param
        if args.sweep_param == 'fuel_mass':
            config['fuel_mass'] = val
        elif args.sweep_param == 'dry_mass':
            config['dry_mass'] = val
        elif args.sweep_param == 'target_apo':
            config['target_apoapsis'] = val
            
        res = run_simulation_batch(config)
        results_alt.append(res.max_altitude)
        
        print(f"Param {val:.1f}: Max Alt = {res.max_altitude/1000:.1f} km, Status={res.status}")
        
    # Plot
    plt.figure()
    plt.plot(values, np.array(results_alt)/1000, 'o-')
    plt.title(f"Sweep: Max Altitude vs {args.sweep_param}")
    plt.xlabel(args.sweep_param)
    plt.ylabel("Max Altitude (km)")
    plt.grid(True)
    plt.savefig(f"{output_dir}/sweep_plot.png")
    print(f"Sweep plot saved to {output_dir}/sweep_plot.png")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rocket Sim Experiment Runner")
    subparsers = parser.add_subparsers(dest='mode', help='Mode')
    
    # Common Args
    parser.add_argument('--planet', default='Earth', help='Planet')
    parser.add_argument('--target_apo', type=float, default=100, help='Target Apoapsis km')
    parser.add_argument('--dry_mass', type=float, default=1000, help='Dry Mass kg')
    parser.add_argument('--fuel_mass', type=float, default=30000, help='Fuel Mass kg')
    parser.add_argument('--propellant', default='liquid', help='Propellant Type')
    
    # Monte Carlo Args
    parser_mc = subparsers.add_parser('mc', help='Monte Carlo Mode')
    parser_mc.add_argument('--runs', type=int, default=10, help='Number of runs')
    parser_mc.add_argument('--noise', type=float, default=5.0, help='Parameter noise percentage (e.g. 5.0 for 5%)')
    parser_mc.add_argument('--save_logs', action='store_true', help='Save CSV logs for all runs')
    
    # Sweep Args
    parser_sweep = subparsers.add_parser('sweep', help='Parameter Sweep Mode')
    parser_sweep.add_argument('--sweep_param', required=True, choices=['fuel_mass', 'dry_mass', 'target_apo'])
    parser_sweep.add_argument('--sweep_min', type=float, required=True)
    parser_sweep.add_argument('--sweep_max', type=float, required=True)
    parser_sweep.add_argument('--sweep_steps', type=int, default=10)
    
    args = parser.parse_args()
    
    if args.mode == 'mc':
        run_monte_carlo(args)
    elif args.mode == 'sweep':
        run_parameter_sweep(args)
    else:
        parser.print_help()
