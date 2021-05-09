"""
@author: Kálley Wilkerson Rodrigues Alexandre 170038050
@author: Rafael 

@description: PyDash Project

An implementation example of an R2A Algorithm based on the Panda algorithm.

the quality list is obtained with the parameter of handle_xml_response() method and the choice
is made inside of handle_segment_size_request(), before sending the message down.

In this algorithm the quality choice is always the same.
"""

from player.parser import *
from r2a.ir2a import IR2A
import time

# Valores constantes
PENULT = 0
LAST = 1


probeAdditiveIncBitrate = 0.3
# Valores possíveis: 0.04,0.07,0.14,0.28,0.42,0.56
probeCongergenceRate = 0.14
# Valores possíveis: 0.05,0.1,0.2,0.3,0.4,0.5
smoothConvergenceRate = 0.2


def find_best_data_rate(avgDataRate, qi):
    result = qi[0]
    print(f'dataRate: {avgDataRate}')
    for r in qi:
        if r < avgDataRate:
            result = r
    print(f'result: {result}')
    return result

class R2APandaBased(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.avgDataRate = []
        self.targetAvgDataRate = []
        self.measuredDataRate = []
        self.interRequestTime = [0.01, 0.01]
        self.targetInterRequestTime = [0.01, 0.01]
        self.segmentDownloadDuration = [0.01, 0.01]
        self.time = 0

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # getting qi list
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        self.measuredDataRate = [self.qi[19], self.qi[19]]
        self.targetAvgDataRate = [self.qi[19], self.qi[19]]

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # Atualizando os tempos de download
        self.interRequestTime[PENULT] = self.interRequestTime[LAST]
        self.interRequestTime[LAST] = max(self.segmentDownloadDuration[LAST], self.targetInterRequestTime[LAST])
        
        # Estimando a largura de banda compartilhada
        temp = self.targetAvgDataRate[LAST]
        self.targetAvgDataRate[LAST] = self.targetAvgDataRate[PENULT] + self.interRequestTime[PENULT]*probeCongergenceRate*(probeAdditiveIncBitrate - max(0, self.targetAvgDataRate[PENULT] - self.measuredDataRate[PENULT] + probeAdditiveIncBitrate))
        self.targetAvgDataRate[PENULT] = temp
        
        # time to define the segment quality choose to make the request
        msg.add_quality_id(find_best_data_rate(self.targetAvgDataRate[LAST], self.qi))

        # Esperando até dá a hora para a próxima requisição
        if time.perf_counter() < (self.time + self.interRequestTime[LAST]):
            time.sleep(self.time + self.interRequestTime[LAST] - time.perf_counter())

        self.time = time.perf_counter()
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        elapsedTime = time.perf_counter() - self.time

        # Atualizando o tempo percorrido
        self.segmentDownloadDuration[PENULT] = self.segmentDownloadDuration[LAST]
        self.segmentDownloadDuration[LAST] = elapsedTime

        # Atualizando as velocidades
        self.measuredDataRate[PENULT] = self.measuredDataRate[LAST]
        self.measuredDataRate[LAST] = msg.get_bit_length() / elapsedTime
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
