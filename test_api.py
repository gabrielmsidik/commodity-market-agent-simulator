"""Test script for the REST API."""

import requests
import time
import json

BASE_URL = "http://localhost:5000"


def test_health():
    """Test health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("✓ Health check passed\n")


def test_default_config():
    """Test default config endpoint."""
    print("Testing default config...")
    response = requests.get(f"{BASE_URL}/api/config/default")
    print(f"Status: {response.status_code}")
    config = response.json()
    print(f"Config keys: {list(config.keys())}")
    assert response.status_code == 200
    assert 'num_days' in config
    print("✓ Default config passed\n")


def test_run_simulation():
    """Test running a simulation."""
    print("Testing simulation run...")
    
    # Start simulation with minimal config
    config = {
        "name": "API Test Simulation",
        "description": "Testing the REST API",
        "num_days": 5  # Short simulation for testing
    }
    
    response = requests.post(
        f"{BASE_URL}/api/simulations/run",
        json=config
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    assert response.status_code == 202
    assert 'job_id' in data
    
    job_id = data['job_id']
    print(f"✓ Simulation started with job_id: {job_id}\n")
    
    # Poll for completion
    print("Polling for completion...")
    max_wait = 300  # 5 minutes max
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status_response = requests.get(
            f"{BASE_URL}/api/simulations/status/{job_id}"
        )
        status_data = status_response.json()
        status = status_data['status']
        
        print(f"  Status: {status}")
        
        if status == 'completed':
            print("✓ Simulation completed\n")
            break
        elif status == 'failed':
            print(f"✗ Simulation failed: {status_data.get('error', 'Unknown error')}")
            return None
        
        time.sleep(5)
    else:
        print("✗ Simulation timed out")
        return None
    
    # Get results
    print("Getting results...")
    results_response = requests.get(
        f"{BASE_URL}/api/simulations/{job_id}"
    )
    results = results_response.json()
    
    print(f"Summary keys: {list(results.get('summary', {}).keys())}")
    print(f"Total market trades: {results['summary']['total_market_trades']}")
    print(f"Average market price: ${results['summary']['average_market_price']:.2f}")
    print("✓ Results retrieved\n")
    
    # Get summary only
    print("Getting summary...")
    summary_response = requests.get(
        f"{BASE_URL}/api/simulations/{job_id}/summary"
    )
    summary = summary_response.json()
    print(f"Summary keys: {list(summary.keys())}")
    print("✓ Summary retrieved\n")
    
    return job_id


def test_list_simulations():
    """Test listing simulations."""
    print("Testing list simulations...")
    response = requests.get(f"{BASE_URL}/api/simulations")
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Total simulations: {data['total']}")
    
    if data['jobs']:
        print(f"First job: {data['jobs'][0]['name']}")
    
    assert response.status_code == 200
    print("✓ List simulations passed\n")


def test_delete_simulation(job_id):
    """Test deleting a simulation."""
    if not job_id:
        print("Skipping delete test (no job_id)\n")
        return
    
    print(f"Testing delete simulation {job_id}...")
    response = requests.delete(f"{BASE_URL}/api/simulations/{job_id}")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    print("✓ Delete simulation passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("API Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_health()
        test_default_config()
        job_id = test_run_simulation()
        test_list_simulations()
        test_delete_simulation(job_id)
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to API server.")
        print("Make sure the server is running: python app.py")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

