import time
import psutil
import cpuinfo
import subprocess
import abc
import argparse
from threading import Timer, current_thread
from distutils.util import strtobool

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class MetricReader:
    def __init__(self, filename, interval=3):
        self.filename = filename
        self.interval = interval


    def write_measurement(self, value):
        current_time = time.strftime("%d.%m.%y %H:%M:%S", time.localtime())
        with open(self.filename, 'a') as f:
            f.write('{} - {}\n'.format(current_time, value))


    def read_value(self):
        pass


    def tick(self):
        self.write_measurement(self.read_value())


    def start(self):
        self.timer = RepeatTimer(self.interval, self.tick)
        self.timer.start()


    def stop(self):
        self.timer.cancel()


class CpuReader(MetricReader):
    def read_value(self):
        return '{} %'.format(psutil.cpu_percent())


class RamReader(MetricReader):
    def __init__(self, filename, interval):
        super().__init__(filename, interval=interval)
        self.total_mem = int(psutil.virtual_memory().total / 1024 / 1024)

    def read_value(self):
        mem = psutil.virtual_memory()
        return '{} MiB / {} MiB'.format(int(mem.used / 1024 / 1024), self.total_mem)


class NvidiaGpuMetricsReader(MetricReader):
    def __init__(self, filename, interval, metric, total_metric=None):
        super().__init__(filename, interval=interval)
        self.cmd = [
                'nvidia-smi',
                '--query-gpu={}'.format(metric),
                '--format=csv,noheader']
        if total_metric:
            self.total_value = subprocess.run([
                'nvidia-smi',
                '--query-gpu={}'.format(total_metric),
                '--format=csv,noheader'], capture_output=True, text=True).stdout.rstrip('\n')

    def read_value(self):
        current_value = subprocess.run(self.cmd, capture_output=True, text=True).stdout.rstrip('\n')
        if hasattr(self, 'total_value'):
            return '{} / {}'.format(current_value, self.total_value)
        else:
            return current_value


class DiskIOReader(MetricReader):
    def start(self):
        counters = psutil.disk_io_counters()
        self.prev_read_bytes = counters[2]
        self.prev_write_bytes = counters[3]
        return super().start()

    def read_value(self):
        counters = psutil.disk_io_counters()
        result =  '{} B / {} B'.format(
            counters[2] - self.prev_read_bytes,
            counters[3] - self.prev_write_bytes
        )
        self.prev_read_bytes = counters[2]
        self.prev_write_bytes = counters[3]

        return result


class NetIOReader(MetricReader):
    def start(self):
        counters = psutil.net_io_counters()
        self.prev_sent_bytes = counters[0]
        self.prev_recv_bytes = counters[1]
        return super().start()

    def read_value(self):
        counters = psutil.net_io_counters()
        result =  '{} B / {} B'.format(
            counters[0] - self.prev_sent_bytes,
            counters[1] - self.prev_recv_bytes
        )
        self.prev_sent_bytes = counters[0]
        self.prev_recv_bytes = counters[1]
        
        return result


def info(args):
    cpu_info = cpuinfo.get_cpu_info()
    


def trace(args):
    readers = []

    if args.cpu:
        readers.append(CpuReader('cpu.txt', args.interval))

    if args.ram:
        readers.append(RamReader('ram.txt', args.interval))
    if args.gpu:
        if 'gr_clock' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_gr_clock.txt', args.interval, 'clocks.gr', 'clocks.max.gr'))
        if 'mem_clock' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_mem_clock.txt', args.interval, 'clocks.mem', 'clocks.max.mem'))
        if 'sm_clock' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_sm_clock.txt', args.interval, 'clocks.sm', 'clocks.max.sm'))
        if 'video_clock' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_video_clock.txt', args.interval, 'clocks.video'))
        if 'fan_speed' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_fan_speed.txt', args.interval, 'fan.speed'))
        if 'mem_usage' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_mem_usage.txt', args.interval, 'memory.used', 'memory.total'))
        if 'power_draw' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_power_draw.txt', args.interval, 'power.draw', 'enforced.power.limit'))
        if 'temp' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_temp.txt', args.interval, 'temperature.gpu'))
        if 'util' in args.gpu:
            readers.append(NvidiaGpuMetricsReader('gpu_util.txt', args.interval, 'utilization.gpu'))

    if args.disk_io:
        readers.append(DiskIOReader('disk_io.txt', args.interval))

    if args.net_io:
        readers.append(NetIOReader('net_io.txt', args.interval))

    try:
        for reader in readers:
            reader.start()
        print('Press any key to stop...')
        input()
    finally:
        for reader in readers:
            reader.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    trace_parser = subparsers.add_parser('trace')
    trace_parser.add_argument('--interval', required=False, default=3, type=int)
    trace_parser.add_argument('--gpu', required=False, choices=['gr_clock', 'mem_clock', 'sm_clock',
        'video_clock', 'fan_speed', 'mem_usage', 'power_draw', 'temp', 'util',], nargs="+")
    trace_parser.add_argument('--cpu', required=False, action='store_true')
    trace_parser.add_argument('--ram', required=False, action='store_true')
    trace_parser.add_argument('--net_io', required=False, action='store_true')
    trace_parser.add_argument('--disk_io', required=False, action='store_true')
    trace_parser.set_defaults(func=trace)

    info_parser = subparsers.add_parser('info')
    info_parser.add_argument('--out', required=False)
    info_parser.add_argument('--cpu', required=False, action='store_true')
    info_parser.add_argument('--ram', required=False, action='store_true')
    info_parser.add_argument('--gpu', required=False, action='store_true')
    info_parser.set_defaults(func=info)

    args = parser.parse_args()
    args.func(args)