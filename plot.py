#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import glob, os, re

# limiar para detectar stall (segundos)
STALL_THRESHOLD = 0.1

# —— parsers ——
def parse_ifstat(path):
    rows = []
    with open(path) as f:
        for l in f:
            p = l.split()
            if len(p)>=3 and re.match(r'^\d+(\.\d+)?$', p[0]):
                rows.append([float(p[0]), float(p[1]), float(p[2])])
    return pd.DataFrame(rows, columns=['time','in_kB','out_kB'])

def parse_iperf(path):
    cols = ['ts','src','sport','dst','dport','id','interval',
            'bytes','bps','jitter','lost','total','ooo','loss_pct']
    df = pd.read_csv(path, header=None, names=cols)
    df[['start','end']] = df['interval'].str.split('-',expand=True).astype(float)
    df = df[df['end']-df['start']<=1.0]  # remove a linha-resumo
    return df

def parse_rtp_jitter(path):
    return pd.read_csv(path, names=['time','jitter_ms'])

def parse_rtp_arrivals(path):
    return pd.read_csv(path, names=['time'])

# —— plot genérico de linha —— 
def plot_line(x, y, xlabel, ylabel, title, out):
    plt.figure()
    plt.plot(x, y)
    plt.xlabel(xlabel); plt.ylabel(ylabel); plt.title(title)
    plt.tight_layout(); plt.savefig(out); plt.close()

# —— detecção e plot de stalls —— 
def detect_and_plot_stalls(arrivals, out_dir):
    df = arrivals.copy()
    df['delta'] = df['time'].diff()
    stalls = df[df['delta'] > STALL_THRESHOLD].copy()
    stalls['start']    = df['time'].shift(1)[stalls.index]
    stalls['duration'] = stalls['delta']

    print(f"\n>>> STALL_THRESHOLD = {STALL_THRESHOLD}s")
    print(f"Stalls encontrados: {len(stalls)}")
    if not stalls.empty:
        print(stalls[['start','duration']].head())

    # timeline de stalls
    plt.figure()
    plt.scatter(stalls['start'], stalls['duration'])
    plt.xlabel('Início do Stall (s)')
    plt.ylabel('Duração do Stall (s)')
    plt.title('Stalls RTP ao Longo do Tempo')
    plt.tight_layout()
    plt.savefig(f'{out_dir}/stalls_timeline.png')
    plt.close()

    # histograma de durações
    plt.figure()
    plt.hist(stalls['duration'], bins=20)
    plt.xlabel('Duração (s)')
    plt.ylabel('Número de Eventos')
    plt.title('Distribuição de Duração de Stalls')
    plt.tight_layout()
    plt.savefig(f'{out_dir}/stalls_histogram.png')
    plt.close()

# —— main —— 
def main():
    out_dir = 'plots'
    os.makedirs(out_dir, exist_ok=True)

    # 1) RTP throughput (ifstat)
    if os.path.isfile('s1-eth3-ifstat.txt'):
        df_if = parse_ifstat('s1-eth3-ifstat.txt')
        plot_line(df_if['time'], df_if['out_kB'],
                  'Tempo (s)', 'Throughput RTP (kB/s)',
                  'RTP Throughput (ifstat)', f'{out_dir}/rtp_throughput.png')

    # 2) Background UDP (iperf)
    for f in sorted(glob.glob('iperf_*.csv')):
        idx = f.split('_')[1].split('.')[0]
        df_ip = parse_iperf(f)
        plot_line(df_ip['end'], df_ip['bps'],
                  'Tempo (s)', 'Throughput UDP (bps)',
                  f'Iperf {idx} Throughput', f'{out_dir}/iperf_{idx}_thr.png')
        plot_line(df_ip['end'], df_ip['jitter'],
                  'Tempo (s)', 'Jitter UDP (ms)',
                  f'Iperf {idx} Jitter', f'{out_dir}/iperf_{idx}_jit.png')

    # 3) RTP jitter (tshark)
    if os.path.isfile('rtp_jitter.csv'):
        df_jit = parse_rtp_jitter('rtp_jitter.csv')
        plot_line(df_jit['time'], df_jit['jitter_ms'],
                  'Tempo (s)', 'Jitter RTP (ms)',
                  'RTP Jitter (tshark)', f'{out_dir}/rtp_jitter.png')

    # 3.5) RTP inter-arrival delays (atrasos entre pacotes)
    if os.path.isfile('rtp_arrivals.csv'):
        df_arr = parse_rtp_arrivals('rtp_arrivals.csv')
        # calcula delta entre chegadas
        df_arr['delta'] = df_arr['time'].diff()
        df_plot = df_arr.dropna()
        plot_line(df_plot['time'], df_plot['delta'],
                  'Tempo (s)', 'Atraso entre Pacotes (s)',
                  'RTP Packet Inter-arrival Delay', f'{out_dir}/rtp_interarrival.png')

    # 4) Stalls em RTP
    if os.path.isfile('rtp_arrivals.csv'):
        df_arr = parse_rtp_arrivals('rtp_arrivals.csv')
        detect_and_plot_stalls(df_arr, out_dir)

    print(f'> Todos os gráficos gerados em ./{out_dir}/')

if __name__=='__main__':
    main()
