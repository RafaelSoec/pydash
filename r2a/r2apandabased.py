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
        else:
            break
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
        self.interRequestTime = [0.001, 0.001]
        self.time = 0

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # getting qi list
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        self.measuredDataRate = [self.qi[0], self.qi[0]]
        self.targetAvgDataRate = [self.qi[0], self.qi[0]]

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.time = time.time()
        
        temp = self.targetAvgDataRate[LAST]
        self.targetAvgDataRate[LAST] = self.targetAvgDataRate[PENULT] + self.interRequestTime[PENULT]*probeCongergenceRate*(probeAdditiveIncBitrate - max(0, self.targetAvgDataRate[PENULT] - self.measuredDataRate[PENULT] + probeAdditiveIncBitrate))
        self.targetAvgDataRate[PENULT] = temp
        
        # time to define the segment quality choose to make the request
        msg.add_quality_id(find_best_data_rate(self.targetAvgDataRate[LAST], self.qi))
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        # Atualizando as velocidades
        self.measuredDataRate[PENULT] = self.measuredDataRate[LAST]
        self.measuredDataRate[LAST] = msg.get_bit_length() / (time.time() - self.time)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
