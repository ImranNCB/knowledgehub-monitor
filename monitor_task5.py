def get_system_info():
	"""Ask the user which system should be  monitored."""
	hostname = input("Hostname: ").strip()
	ip_address = input("IP address: ").strip()

	return hostname, ip_address

def get_metrics():
	"""Ask the user which metrics should be monitored."""
	metrics_input = input(
           "Metrics (comma separated, e.g. cpu,memory,disk): "
	)

	return [
	    metric.strip()
	    for metric in metrics_input.split(",")
	    if metric.strip()
	]


def display_configuration(hostname, ip_address, metrics):
    """Display the monitoring configuration."""
    print("\n--- Monitoring Configuration ---")
    print(f"Hostname : {hostname}")
    print(f"IP       : {ip_address}")
    print("Metrics   :")

    for metric in metrics:
        print(f"  -{metric}")


def main():
    hostname, ip_address = get_system_info()
    metrics = get_metrics()

    display_configuration(hostname, ip_address, metrics)



if __name__ == "__main__":
    main()
