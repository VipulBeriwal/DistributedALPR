from openalpr import Alpr
import cv2, sys, time, numpy, zmq, time, json, os, pickle


ALPR = None
NO_OF_SPECULATIONS = 0
COUNTRY_REGION = ""
CONFIDENCE = 0
PLATES_REPOSITORY = None
MATCHING_LENGTH = 0


class Frame_Data():
    def __init__(self, path_to_frame, server_identity, time, matched_plates):
        self.byte_frame = cv2.imencode('.jpg', cv2.imread(path_to_frame, cv2.IMREAD_COLOR) )[1].tostring()
        self.server_identity = server_identity
        self.time = time
        self.matched_plates = matched_plates



def Initialize(no_of_speculations, country_region, confidence):
    global ALPR, NO_OF_SPECULATIONS, COUNTRY_REGION, CONFIDENCE, PLATES_REPOSITORY, MATCHING_LENGTH
    ALPR = Alpr("us", "/etc/openalpr/openalpr.conf", "/usr/share/openalpr/runtime_data")
    
    if not ALPR.is_loaded():
        print("Error loading OpenAlpr")
        sys.exit(1)
    
    ALPR.set_top_n(no_of_speculations)
    ALPR.set_default_region(country_region)
    NO_OF_SPECULATIONS = no_of_speculations
    COUNTRY_REGION = country_region
    CONFIDENCE = confidence
    PLATES_REPOSITORY = ["710CAS"]
    MATCHING_LENGTH = 3
    


def Identify_Frame(path_to_frame, server_identity):
    global ALPR, NO_OF_SPECULATIONS, COUNTRY_REGION, CONFIDENCE, PLATES_REPOSITORY, MATCHING_LENGTH
    results = ALPR.recognize_file(path_to_frame)
    matched_plates = []
    
    for plate in results['results']:
        for candidate in plate['candidates']:
                
            if candidate['confidence'] >= CONFIDENCE:
                for x in PLATES_REPOSITORY:
                    length = LongestCommonString(x, candidate['plate'], len(x), len(candidate['plate']))
                        
                    if length >= MATCHING_LENGTH:
                        matched_plates.append([x, str(candidate['plate']), candidate['confidence']])

    if len(matched_plates) > 0:
        return Frame_Data(path_to_frame, server_identity, time.asctime(time.localtime(time.time())), matched_plates)
    else: return None


#returns the length of longest common substring matched
def LongestCommonString(X, Y, m, n):  
    LCSuff = [[0 for k in range(n+1)] for l in range(m+1)] 
    result = 0 
      
    for i in range(m + 1): 
        for j in range(n + 1): 
            if (i == 0 or j == 0): 
                LCSuff[i][j] = 0
            elif (X[i-1] == Y[j-1]): 
                LCSuff[i][j] = LCSuff[i-1][j-1] + 1
                result = max(result, LCSuff[i][j]) 
            else: 
                LCSuff[i][j] = 0
    return result



Initialize(2, "ca", 50)
path = os.getcwd() + "/frame.jpeg"
data = Identify_Frame(path, 3)





context = zmq.Context()
socket = context.socket(zmq.PUSH)
socket.connect("tcp://127.0.0.1:9999")
if data:
    socket.send(pickle.dumps(data))
    print("data sent")
