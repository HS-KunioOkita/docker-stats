import os
import docker
import statistics
from threading import Thread

TARGET_CONTAINERS = 'target_containers.csv'

class CpuiUtilizationMonitor(Thread):
    # 平均で50%を超えている場合は、強制的に再起動する。
    CPU_USAGE_THRESHOLD = 50
    # ここで設定した回数分の値を取得する。
    CPU_MONITOR_TOTAL_COUNT = 5

    def __init__(self, container_id):
        self.container_id = container_id
        super(CpuiUtilizationMonitor, self).__init__()

    def run(self):
        print(f"Start cpu monitor. conainer_id : {self.container_id}")
        client = docker.from_env()
        container = client.containers.get(self.container_id)

        if container.status == 'exited':
            print(f"Stop cpu monitor. Container is exited. {self.container_id}")
            return

        cpu_usage_values = []
        for stats in container.stats(decode=True, stream=True):
            if counter > self.CPU_MONITOR_TOTAL_COUNT:
                break

            cpu_usage_percentage = self.calc_cpu_usage_percentage(stats)
            cpu_usage_values.append(cpu_usage_percentage)
            print('{},{},{:.2f}%'.format(counter, self.container_id, cpu_usage_percentage))
            counter += 1

        if statistics.mean(cpu_usage_values) > self.CPU_USAGE_THRESHOLD:
            print(f'restart container. id = {self.container_id}')
            container.restart()

        print(f"Stop cpu monitor. for {self.container_id}")

    def calc_cpu_usage_percentage(self, container_stats):
        print(container_stats)
        cpu_stats = container_stats['cpu_stats']
        precpu_stats = container_stats['precpu_stats']
        cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
        system_cpu_delta = cpu_stats['system_cpu_usage'] - (precpu_stats['system_cpu_usage'] if ('system_cpu_usage' in precpu_stats) else 0)
        number_cpus = cpu_stats['online_cpus']
        cpu_percentage = (cpu_delta / system_cpu_delta) * number_cpus * 100.0
        return cpu_percentage

def main():
    container_ids = load_target_containers()
    if container_ids == False:
        return

    print('monitor start', container_ids)
    for container_id in container_ids:
        th = CpuiUtilizationMonitor(container_id)
        th.start()


def load_target_containers():
    if os.environ.get("MONITOR_CONTAINER_IDS") is None:
        try:
            with open(TARGET_CONTAINERS) as f:
                    container_ids = list(map(lambda line: line.rstrip(), f.readlines()))
                    return container_ids
        except Exception as e:
            print(e)
            return False
    else:
        container_ids = os.environ.get("MONITOR_CONTAINER_IDS").split(",")
        return container_ids

if __name__ == '__main__':
    main()
