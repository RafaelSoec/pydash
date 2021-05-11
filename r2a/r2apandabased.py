"""
@author: Kálley Wilkerson Rodrigues Alexandre - 170038050
@author: Rafael Oliveira de Souza - 150081537

@description: PyDash Project

An implementation example of an R2A Algorithm based on the Panda algorithm.
"""

from player.parser import *
from r2a.ir2a import IR2A
import time

# Valores constantes
PENULT = 0
LAST = 1

# Parâmetros criados
MI_PARAM = 25000
LAST_WEIGHT = 0.6

probeAdditiveIncBitrate = 0.3
# Valores possíveis: 0.04,0.07,0.14,0.28,0.42,0.56
probeCongergenceRate = 0.28
# Valores possíveis: 0.05,0.1,0.2,0.3,0.4,0.5
smoothConvergenceRate = 0.2


def find_best_data_rate(avgDataRate, qi):
    result = qi[0]
    for r in qi:
        if r < avgDataRate:
            result = r
    return result

def smooth_data_rate(*data_rates):
    result = 0
    for dr in data_rates:
        result += dr
    return result/len(data_rates)

class R2APandaBased(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.avgDataRate = []
        self.targetAvgDataRate = []
        self.measuredDataRate = []
        self.segmentDownloadDuration = [0.01, 0.01]

        self.bufferDuration = [0.0, 0.0]
        self.segmentTime = 0.0017
        self.bufferMinDuration = 26
        self.clientBufferConvergenceRate = 0.2

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # getting qi list
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        elapsed_time = time.perf_counter() - self.request_time
        data_rate = find_best_data_rate(msg.get_bit_length()/elapsed_time, self.qi)

        self.measuredDataRate = [data_rate, data_rate]
        self.targetAvgDataRate = [data_rate, data_rate]

        self.interRequestTime = [elapsed_time, elapsed_time]
        self.targetInterRequestTime = [elapsed_time, elapsed_time]
        self.segmentDownloadDuration = [elapsed_time, elapsed_time]

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # Estimando a largura de banda compartilhada
        temp = self.targetAvgDataRate[LAST]
        MI = 0
        if self.interRequestTime[PENULT] < 1:
            MI = MI_PARAM/self.interRequestTime[PENULT]
        else:
            MI = MI_PARAM/(5*self.interRequestTime[PENULT])
        AIMD = probeCongergenceRate*(probeAdditiveIncBitrate - max(0, self.targetAvgDataRate[PENULT] - self.measuredDataRate[PENULT] + probeAdditiveIncBitrate))
        self.targetAvgDataRate[LAST] = self.targetAvgDataRate[PENULT] + self.interRequestTime[PENULT]*AIMD + MI
        self.targetAvgDataRate[PENULT] = temp

        # Recuperando o valor caso caia demais e fique negativo
        if self.targetAvgDataRate[LAST] < 0:
            self.targetAvgDataRate[LAST] = self.measuredDataRate[LAST]/2

        # Refinando o valor obitido para a taxa de transferência calculada acima
        self.targetAvgDataRate[LAST] = smooth_data_rate(self.targetAvgDataRate[PENULT], self.targetAvgDataRate[LAST])

        print('\n--------------------------------')
        print(f'times: {self.interRequestTime[PENULT]}, {self.interRequestTime[LAST]}')
        print(f'data rates: {self.targetAvgDataRate[PENULT]}, {self.targetAvgDataRate[LAST]}')
        print('--------------------------------\n')

        # time to define the segment quality choose to make the request
        data_rate = find_best_data_rate(self.targetAvgDataRate[LAST], self.qi)
        msg.add_quality_id(data_rate)

        # Calculando o tempo para a próxima requisição
        self.targetInterRequestTime[PENULT] = self.targetInterRequestTime[LAST]
        self.targetInterRequestTime[LAST] = (data_rate*self.segmentTime/self.targetAvgDataRate[LAST]) + self.clientBufferConvergenceRate*(self.bufferDuration[PENULT] - self.bufferMinDuration)

        # Atualizando os tempos de download
        self.interRequestTime[PENULT] = self.interRequestTime[LAST]
        self.interRequestTime[LAST] = max(self.segmentDownloadDuration[LAST], self.targetInterRequestTime[LAST])
        
        # Esperando até dá a hora para a próxima requisição
        if time.perf_counter() < (self.request_time + self.interRequestTime[LAST]):
            time.sleep(self.request_time + self.interRequestTime[LAST] - time.perf_counter())

        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        elapsedTime = time.perf_counter() - self.request_time

        # Atualizando o tempo percorrido
        self.segmentDownloadDuration[PENULT] = self.segmentDownloadDuration[LAST]
        self.segmentDownloadDuration[LAST] = elapsedTime

        # Atualizando dados de buffer
        temp = self.bufferDuration[LAST]
        self.bufferDuration[LAST] = max(0, self.bufferDuration[PENULT] + self.segmentTime - self.interRequestTime[LAST])
        self.bufferDuration[PENULT] = temp

        # Atualizando as velocidades
        self.measuredDataRate[PENULT] = self.measuredDataRate[LAST]
        self.measuredDataRate[LAST] = msg.get_bit_length() / elapsedTime
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
