import heapq
import random

class SimuladorTandem:
    def __init__(self, config_rede, max_aleatorios=100000, semente=42):
        self.config = config_rede
        self.max_aleatorios = max_aleatorios
        self.aleatorios_consumidos = 0
        
        # Estado das filas
        self.filas = {}
        for nome, params in self.config.items():
            self.filas[nome] = {
                'tamanho_atual': 0,
                'perdas': 0,
                'tempos_estado': {i: 0.0 for i in range(params['capacidade'] + 1)}
            }
            
        self.tempo_atual = 0.0
        self.tempo_anterior = 0.0
        self.eventos = []  # Fila de prioridade (heap)
        
        # Inicializando o gerador de números aleatórios com semente para reprodutibilidade
        self.rng = random.Random(semente)

    def gerar_aleatorio(self, minimo, maximo):
        """Gera um número uniforme e controla o consumo de números aleatórios."""
        if self.aleatorios_consumidos >= self.max_aleatorios:
            raise StopIteration("Limite de números aleatórios atingido.")
        
        self.aleatorios_consumidos += 1
        # U(a,b) = a + (b-a) * U(0,1)
        return minimo + (maximo - minimo) * self.rng.random()

    def agendar_evento(self, tempo, tipo_evento, nome_fila):
        heapq.heappush(self.eventos, (tempo, tipo_evento, nome_fila))

    def atualizar_tempos(self, tempo_evento):
        delta = tempo_evento - self.tempo_atual
        for nome, estado in self.filas.items():
            tam = estado['tamanho_atual']
            estado['tempos_estado'][tam] += delta
        self.tempo_atual = tempo_evento

    def determinar_destino(self, nome_fila):
        """Define para onde o cliente vai com base nas probabilidades de roteamento."""
        roteamento = self.config[nome_fila]['roteamento']
        r = self.rng.random()
        # Não contamos essa chamada de random para roteamento como parte dos tempos 
        # (mas caso seja uma exigência rigorosa, pode-se usar self.gerar_aleatorio(0, 1))
        
        acumulado = 0.0
        for destino, prob in roteamento.items():
            acumulado += prob
            if r <= acumulado:
                return destino
        return 'Saida'

    def chegada(self, nome_fila):
        params = self.config[nome_fila]
        estado = self.filas[nome_fila]
        
        # Se for uma fila com chegadas externas, agenda a próxima chegada do exterior
        if params['chegadas'] is not None:
            tempo_prox_chegada = self.tempo_atual + self.gerar_aleatorio(*params['chegadas'])
            self.agendar_evento(tempo_prox_chegada, 'CHEGADA', nome_fila)

        # Processa a entrada do cliente na fila
        if estado['tamanho_atual'] < params['capacidade']:
            estado['tamanho_atual'] += 1
            # Se o tamanho for menor ou igual ao número de servidores, o atendimento começa imediatamente
            if estado['tamanho_atual'] <= params['servidores']:
                tempo_atendimento = self.tempo_atual + self.gerar_aleatorio(*params['atendimento'])
                self.agendar_evento(tempo_atendimento, 'SAIDA', nome_fila)
        else:
            estado['perdas'] += 1

    def saida(self, nome_fila):
        params = self.config[nome_fila]
        estado = self.filas[nome_fila]
        
        estado['tamanho_atual'] -= 1
        
        # Se ainda há clientes esperando na fila, agenda a saída do próximo
        if estado['tamanho_atual'] >= params['servidores']:
            tempo_atendimento = self.tempo_atual + self.gerar_aleatorio(*params['atendimento'])
            self.agendar_evento(tempo_atendimento, 'SAIDA', nome_fila)
            
        # Roteamento do cliente que acabou de ser atendido
        destino = self.determinar_destino(nome_fila)
        if destino != 'Saida':
            # Simula a chegada do cliente na próxima fila
            estado_destino = self.filas[destino]
            params_destino = self.config[destino]
            
            if estado_destino['tamanho_atual'] < params_destino['capacidade']:
                estado_destino['tamanho_atual'] += 1
                if estado_destino['tamanho_atual'] <= params_destino['servidores']:
                    tempo_atend = self.tempo_atual + self.gerar_aleatorio(*params_destino['atendimento'])
                    self.agendar_evento(tempo_atend, 'SAIDA', destino)
            else:
                estado_destino['perdas'] += 1

    def executar(self, tempo_primeira_chegada=1.5):
        # Agenda a primeira chegada para a Fila 1 (ou qualquer fila com chegadas externas)
        for nome, params in self.config.items():
            if params['chegadas'] is not None:
                self.agendar_evento(tempo_primeira_chegada, 'CHEGADA', nome)

        try:
            while self.eventos:
                tempo_evento, tipo_evento, nome_fila = heapq.heappop(self.eventos)
                self.atualizar_tempos(tempo_evento)
                
                if tipo_evento == 'CHEGADA':
                    self.chegada(nome_fila)
                elif tipo_evento == 'SAIDA':
                    self.saida(nome_fila)
                    
        except StopIteration:
            # O simulador é interrompido no exato momento em que o 100.000º número aleatório é requisitado
            pass
            
        self.relatorio()

    def relatorio(self):
        print("="*50)
        print("RELATÓRIO DA SIMULAÇÃO DE FILAS EM TANDEM")
        print("="*50)
        print(f"Tempo Global da Simulação: {self.tempo_atual:.4f}")
        print(f"Números Aleatórios Consumidos: {self.aleatorios_consumidos}\n")

        for nome, estado in self.filas.items():
            print(f"--- {nome} ---")
            print("Estado | Tempo Acumulado | Probabilidade (%)")
            
            tempos = estado['tempos_estado']
            tempo_total_fila = sum(tempos.values())
            
            for i in range(len(tempos)):
                tempo = tempos[i]
                prob = (tempo / tempo_total_fila) * 100 if tempo_total_fila > 0 else 0
                print(f"  {i:2d}   |  {tempo:14.4f} |  {prob:14.2f}%")
                
            print(f"Total de perdas: {estado['perdas']} cliente(s)\n")

# =====================================================================
# Cenário de Validação
# =====================================================================
if __name__ == "__main__":
    rede_validacao = {
        'Fila 1': {
            'chegadas': (1.0, 4.0),
            'atendimento': (3.0, 4.0),
            'servidores': 2,
            'capacidade': 3,
            'roteamento': {'Fila 2': 1.0}  # 100% dos clientes vão para a Fila 2
        },
        'Fila 2': {
            'chegadas': None, # Não possui chegadas externas
            'atendimento': (2.0, 3.0),
            'servidores': 1,
            'capacidade': 5,
            'roteamento': {'Saida': 1.0}  # 100% dos clientes vão embora
        }
    }

    # Inicializando com chegada inicial em 1.5 e limite de 100.000 aleatórios
    simulador = SimuladorTandem(rede_validacao, max_aleatorios=100000, semente=42)
    simulador.executar(tempo_primeira_chegada=1.5)