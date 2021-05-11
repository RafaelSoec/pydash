"""
@author: Rafael Oliveira de Souza - 150081537 
@author: Kálley Wilkerson Rodrigues Alexandre - 170038050

@description: PyDash Project

An implementation example of an R2A Algorithm based on the Bola algorithm.
"""

from r2a.ir2a import IR2A
from player.parser import *
from base.timer import Timer
import numpy as np
import time

# Esta classe pretende representar o algoritimo ABR usando a implementação BOLA.
#  BOLA (Buffer Occupancy based Lyapunov Algorithm)


class IR2A_BOLA(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.qi = []
        self.throughput = 0
        self.request_time = 0
        self.vM = 0
        self.timer = Timer.get_instance()
        self.pause_started_at = None

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # executar o parser do arquivo
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()
        # enviar a resposta
        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # O video foi segmentado de 6 maneiras diferentes e codificado em 20 formatos distintos
        QTD_FORMAT = 20

        #  Tamanho maximo do buffer
        Q_MAX = self.whiteboard.get_max_buffer_size()

        # Implementacao dinamica
        # T_MIN = min(t_in, t_out)
        # T_RES = max((T_MIN/2), 3)
        # Q_MAX = min(Q_MAX, T_RES)

        #  GAMMA_PARAMETER corresponde à intensidade com que queremos evitar o rebuffering.
        #  TODO -  Poderia ser um valor dinamico, mas por simplicidade esta sendo inicializado manualmente
        # GAMMA_PARAMETER = 7
        GAMMA_PARAMETER = self.timer.get_started_time()

        # Um desafio de implantação envolve a escolha do BOLA parâmetros γ(GAMMA_PARAMETER) e V(PARAM).
        # Parâmetro de controle definido pelo Bola para possibilitar troca entre o tamanho do buffer e desempenho
        PARAM = ((Q_MAX - 1) / (self.vM + GAMMA_PARAMETER))

        # Salva em buffers = A lista de tamanho dos buffers - o tamanho maximo do buffer é 60
        buffers = self.whiteboard.get_playback_buffer_size()
        # Ennquanto o video não tem inicio o buffer é definido como 0
        if not buffers:
            buffers = ([0, 0], [0, 0])
        # Seleciona o valor mais atual para o nível do buffer
        current_buffer = buffers[-1]

        # time.perf_counter() retorna o tempo em que a mensagem será encaminhada para o singletton ConnectionHandler
        # request_time será usada posteriormente para calcular o valor de throughput
        self.request_time = time.perf_counter()

        # Escolhe o indice de qualidade
        # m = taxa de bits
        # Param = Vd, Sm = self.qi[i], S1 = self.qi[0]
        m = 0
        selected_qi = 1
        for i in range(QTD_FORMAT):
            #   função de utilidade logarítmica
            self.vM = np.log(self.qi[i] / self.qi[0])
            m_actual = ((PARAM * self.vM) + (PARAM * GAMMA_PARAMETER) -
                        current_buffer[1]) / self.qi[i]

            # Define o maior valor para a variavel m_actual
            if m < m_actual:
                m = m_actual
                selected_qi = i

                # salva em playback_qi = A lista com o índice de qualidade do vídeo
                playback_qi = self.whiteboard.get_playback_qi()
                # Verifica a lista com o índice de qualidade do vídeo
                if len(playback_qi) > 0:
                    ind_seg_ant = playback_qi[-1][1]
                    # Verifica se indice de qualidade definido é maior que o indice do segmento anterior,
                    if selected_qi > ind_seg_ant:
                        m_line = 0
                        max_val = self.qi[0]
                        if (self.throughput >= self.qi[0]):
                            max_val = self.throughput
                        for j in range(QTD_FORMAT):
                            if (m_line <= j and self.qi[j] <= max_val):
                                m_line = j
                        # O indice é setado com um novo valor caso ele esteja incluido nos  indices antigos
                        # Pro caso contrário o indice é setado com o valor do indice antigo
                        if (m_line < ind_seg_ant):
                            m_line = ind_seg_ant
                        elif (m_line >= m):
                            m_line = selected_qi
                        # TODO - Verificar metodo de pausa
                        # Verifica se houve uma oscilação grande entre o ultimo inndice e o indice anterior
                        # elif (m_line > (GAMMA_PARAMETER + ind_seg_ant)):
                        #     selected_qi = ind_seg_ant
                        #     if(i+1 < QTD_FORMAT):
                        #         next_vM = np.log(self.qi[i+1] / self.qi[i])
                        #         m_next = ((PARAM * next_vM) + (PARAM * GAMMA_PARAMETER) -
                        #                   current_buffer[1]) / self.qi[i+1]

                        #         if m_actual > m_next:
                        #             continue
                        else:
                            m_line += 1

                        selected_qi = m_line
            else:
                self.pause_started_at = None
                self.buffer = [0, 0]

        msg.add_quality_id(self.qi[selected_qi])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        # tempDuracao = tempo de duração entre a ida e a volta da mensagem ao ConnectionHandler
        tempDuracao = time.perf_counter() - self.request_time

        # Determina o throughput sobre a requisição do segmento de vídeo
        self.throughput = msg.get_bit_length() / tempDuracao

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
