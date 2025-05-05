# Técnicas de QoS

## O que tentamos e não funcionou:
- **Strict Priority Queuing** usando qdisc `prio` (Formação de filas por prioridade)  
  Implementado como filha da classe HTB padrão, criou três bandas de prioridade (0 > 1 > 2) mas ainda houve jitter próximo ao fim do experimento :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}.  
- **Traffic Shaping com TBF** (Token Bucket Filter / Balde de fichas)  
  Suavizou rajadas de vídeo, mas não eliminou o jitter sob carga de iperf :contentReference[oaicite:2]{index=2}:contentReference[oaicite:3]{index=3}.  
- **HTB + FQ_CoDel inicial**  
  Tentativa de usar HTB para reserva de banda e FQ_CoDel para combate a bufferbloat, porém interrompeu a reprodução antes de concluir o streaming.

## O que utilizamos e funcionou como solução final:
- **Resource Reservation com HTB**  
  Duas classes HTB com `rate = ceil` fixo (6 Mbit/s para RTP e 4 Mbit/s para Best-Effort), garantindo banda mínima absoluta ao fluxo sensível :contentReference[oaicite:4]{index=4}:contentReference[oaicite:5]{index=5}.  
- **FQ_CoDel** na classe RTP  
  Mantém filas curtas e adapta dinamicamente o descarte para controlar o atraso médio (target=5 ms), reduzindo significativamente o jitter sem interromper o vídeo.  
- **Stochastic Fair Queuing (SFQ)** na classe Best-Effort  
  Divide a banda remanescente de forma justa entre múltiplos fluxos iperf, evitando que eles monopolizem a cota de 4 Mbit/s :contentReference[oaicite:6]{index=6}:contentReference[oaicite:7]{index=7}.  





A técnica que você está usando combina Resource Reservation via HTB (Hierarchical Token Bucket) com fq_codel para lidar com bufferbloat e SFQ para fairness em cargas best-effort. Veja os detalhes de cada componente e, em seguida, como coletar métricas para gerar gráficos no seu relatório:

HTB (Hierarchical Token Bucket)
um algoritmo de token bucket, só que hierárquico. Ele permite criar classes com rate=ceil fixo (reservas rígidas), mas dentro de uma estrutura de árvore de classes.

FQ_CoDel

Para a classe RTP, controla dinamicamente a fila e elimina o bufferbloat, reduzindo jitter.

SFQ (Stochastic Fair Queuing)

Na classe best-effort, distribui a banda restante de forma justa entre fluxos iperf.


## Coletar metricas 
...

## Gerar graficos
...


## Comparacao sem 

