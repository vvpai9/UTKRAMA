import csv
import json
import os
import numpy as np

class SimulationLogger:
    @staticmethod
    def export_to_csv(history, filename):
        """
        Exports the history dictionary to a CSV file.
        """
        keys = list(history.keys())
        if not keys:
            return
            
        # Ensure all lists are same length
        length = len(history[keys[0]])
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            
            for i in range(length):
                row = []
                for k in keys:
                    val = history[k][i] if i < len(history[k]) else ""
                    if isinstance(val, (int, float)):
                        row.append(f"{val:.4f}")
                    else:
                        row.append(str(val))
                writer.writerow(row)
                
    @staticmethod
    def export_to_json(metadata, history, filename):
        """
        Exports metadata and decimated history to JSON.
        """
        # Convert numpy types to native python types for JSON serialization
        def default_converter(o):
            if isinstance(o, np.integer): return int(o)
            if isinstance(o, np.floating): return float(o)
            if isinstance(o, np.ndarray): return o.tolist()
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

        data = {
            "metadata": metadata,
            "history": history
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4, default=default_converter)
