"""Simple Flask API server for running simulations."""

import logging
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS

from src.simulation import SimulationConfig, SimulationRunner

# In-memory storage for jobs and results
jobs: Dict[str, Dict[str, Any]] = {}
results: Dict[str, Dict[str, Any]] = {}
jobs_lock = threading.Lock()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_simulation_async(job_id: str, config_dict: Dict[str, Any]):
    """Run simulation in background thread."""
    try:
        with jobs_lock:
            jobs[job_id]['status'] = 'running'
            jobs[job_id]['started_at'] = datetime.now().isoformat()

        # Create config from dictionary
        config = SimulationConfig(**config_dict)

        logger.info(f"Starting simulation {job_id} with config: {config}")

        # Run simulation
        runner = SimulationRunner(config, log_level=logging.INFO)
        result = runner.run()

        # Store results
        with jobs_lock:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
            results[job_id] = result

        logger.info(f"Simulation {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Simulation {job_id} failed: {str(e)}", exc_info=True)
        with jobs_lock:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = str(e)
            jobs[job_id]['completed_at'] = datetime.now().isoformat()


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/config/default', methods=['GET'])
def get_default_config():
    """Get default simulation configuration."""
    config = SimulationConfig()
    return jsonify({
        'name': config.name,
        'description': config.description,
        'num_days': config.num_days,
        's1_cost_min': config.s1_cost_min,
        's1_cost_max': config.s1_cost_max,
        's1_inv_min': config.s1_inv_min,
        's1_inv_max': config.s1_inv_max,
        's1_starting_cash': config.s1_starting_cash,
        's2_cost_min': config.s2_cost_min,
        's2_cost_max': config.s2_cost_max,
        's2_inv_min': config.s2_inv_min,
        's2_inv_max': config.s2_inv_max,
        's2_starting_cash': config.s2_starting_cash,
        'w_starting_cash': config.w_starting_cash,
        'total_shoppers': config.total_shoppers,
        'long_term_ratio': config.long_term_ratio,
        'lt_base_min': config.lt_base_min,
        'lt_base_max': config.lt_base_max,
        'lt_max_min': config.lt_max_min,
        'lt_max_max': config.lt_max_max,
        'lt_urgency_min': config.lt_urgency_min,
        'lt_urgency_max': config.lt_urgency_max,
        'st_base_min': config.st_base_min,
        'st_base_max': config.st_base_max,
        'st_max_min': config.st_max_min,
        'st_max_max': config.st_max_max,
        'st_urgency_min': config.st_urgency_min,
        'st_urgency_max': config.st_urgency_max
    })


@app.route('/api/simulations/run', methods=['POST'])
def run_simulation():
    """Start a new simulation (async)."""
    try:
        config_dict = request.json

        if not config_dict:
            return jsonify({'error': 'No configuration provided'}), 400

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Store job info
        with jobs_lock:
            jobs[job_id] = {
                'job_id': job_id,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'config': config_dict
            }

        # Start simulation in background thread
        thread = threading.Thread(
            target=run_simulation_async,
            args=(job_id, config_dict),
            daemon=True
        )
        thread.start()

        logger.info(f"Started simulation job {job_id}")

        return jsonify({
            'job_id': job_id,
            'status': 'pending',
            'message': 'Simulation started'
        }), 202

    except Exception as e:
        logger.error(f"Failed to start simulation: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulations/status/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get status of a simulation job."""
    with jobs_lock:
        job = jobs.get(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    response = {
        'job_id': job_id,
        'status': job['status'],
        'created_at': job['created_at']
    }

    if 'started_at' in job:
        response['started_at'] = job['started_at']

    if 'completed_at' in job:
        response['completed_at'] = job['completed_at']

    if 'error' in job:
        response['error'] = job['error']

    return jsonify(response)


@app.route('/api/simulations/<job_id>', methods=['GET'])
def get_simulation_results(job_id: str):
    """Get results of a completed simulation."""
    with jobs_lock:
        job = jobs.get(job_id)
        result = results.get(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if job['status'] != 'completed':
        return jsonify({
            'error': f"Simulation not completed. Current status: {job['status']}"
        }), 400

    if not result:
        return jsonify({'error': 'Results not found'}), 404

    return jsonify(result)


@app.route('/api/simulations/<job_id>/summary', methods=['GET'])
def get_simulation_summary(job_id: str):
    """Get summary of a completed simulation."""
    with jobs_lock:
        job = jobs.get(job_id)
        result = results.get(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if job['status'] != 'completed':
        return jsonify({
            'error': f"Simulation not completed. Current status: {job['status']}"
        }), 400

    if not result:
        return jsonify({'error': 'Results not found'}), 404

    # Return only the summary
    return jsonify(result.get('summary', {}))


@app.route('/api/simulations', methods=['GET'])
def list_simulations():
    """List all simulation jobs."""
    with jobs_lock:
        job_list = [
            {
                'job_id': job_id,
                'status': job['status'],
                'created_at': job['created_at'],
                'name': job['config'].get('name', 'Unnamed'),
                'description': job['config'].get('description', '')
            }
            for job_id, job in jobs.items()
        ]

    # Sort by created_at descending
    job_list.sort(key=lambda x: x['created_at'], reverse=True)

    return jsonify({
        'total': len(job_list),
        'jobs': job_list
    })


@app.route('/api/simulations/<job_id>', methods=['DELETE'])
def delete_simulation(job_id: str):
    """Delete a simulation job and its results."""
    with jobs_lock:
        if job_id not in jobs:
            return jsonify({'error': 'Job not found'}), 404

        del jobs[job_id]
        if job_id in results:
            del results[job_id]

    return jsonify({'message': 'Simulation deleted'}), 200


if __name__ == '__main__':
    logger.info("Starting Flask API server...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )


