class Measurement():
    # a measurement name
    def __init__(self, name=None):
        self.dataset_index = 0 # measurement = 0, marker = 1, axis = 2, angle = 3
        self.name  = name

class Marker():
    # a marker name
    def __init__(self, name=None):
        self.dataset_index = 1 # measurement = 0, marker = 1, axis = 2, angle = 3
        self.name  = name
    
class Axis():
    # an axis name
    def __init__(self, name=None):
        self.dataset_index = 2 # measurement = 0, marker = 1, axis = 2, angle = 3
        self.name  = name

class Angle():
    # an angle name
    def __init__(self, name=None):
        self.dataset_index = 3 # measurement = 0, marker = 1, axis = 2, angle = 3
        self.name  = name

class AxisFunctions():

    def parameters(self):
    # default parameters of axis functions
        return [
            [
                # pelvis_axis parameters
                Marker('RASI'), Marker('LASI'),
                Marker('RPSI'), Marker('LPSI'),
                Marker('SACR')
            ],

            [
                # hip_joint_center parameters
                Axis('Pelvis'), Measurement('MeanLegLength'),
                Measurement('R_AsisToTrocanterMeasure'),
                Measurement('L_AsisToTrocanterMeasure'),
                Measurement('InterAsisDistance')
            ],

            [
                # hip_axis parameters
                Axis('RHipJC'),
                Axis('LHipJC'),
                Axis('Pelvis')
            ],

            [
                # knee_axis parameters
                Marker('RTHI'), Marker('LTHI'),
                Marker('RKNE'), Marker('LKNE'),
                Axis('RHipJC'), Axis('LHipJC'),
                Measurement('RightKneeWidth'),
                Measurement('LeftKneeWidth')
            ],

            [
                # ankle_axis parameters
                Marker('RTIB'), Marker('LTIB'),
                Marker('RANK'), Marker('LANK'),
                Axis('RKnee'),  Axis('LKnee'),
                Measurement('RightAnkleWidth'),
                Measurement('LeftAnkleWidth'),
                Measurement('RightTibialTorsion'),
                Measurement('LeftTibialTorsion')
            ],

            [
                # foot_axis parameters
                # no function?
            ],

            [
                # head_axis parameters
                # no function?
            ],

            [
                # thorax_axis parameters
                Marker('CLAV'), Marker('C7'),
                Marker('STRN'), Marker('T10')
            ],

            [
                # clav_axis/shoulder_axis parameters
                # no function?
            ],

            [
                # hum_axis/elbow_joint_center parameters
                Marker('RELB'), Marker('LELB'),
                Marker('RWRA'), Marker('RWRB'),
                Marker('LWRA'), Marker('LWRB'),
                Axis('RClav'),  Axis('LClav'),
                Measurement('RightElbowWidth'),
                Measurement('LeftElbowWidth'),
                Measurement('RightWristWidth'),
                Measurement('LeftWristWidth'),
                7.0  # marker mm
            ],

            [
                # rad_axis/wrist_axis parameters
                Axis('RHum'),     Axis('LHum'),
                Axis('RWristJC'), Axis('LWristJC')
            ],

            [
                # hand_axis parameters
                Marker('RWRA'),   Marker('RWRB'),
                Marker('LWRA'),   Marker('LWRB'),
                Marker('RFIN'),   Marker('LFIN'),
                Axis('RWristJC'), Axis('LWristJC'),
                Measurement('RightHandThickness'),
                Measurement('LeftHandThickness')
            ],
        ]
class AngleFunctions():
    # default parameters of angle functions

    def parameters(self):
        return [

            [
                # pelvis_angle parameters
                Measurement('GCS'),
                Axis('Pelvis')
            ],

            [
                # hip_angle parameters
                Axis('Hip'), Axis('RKnee'),
                Axis('Hip'), Axis('LKnee')
            ],

            [
                # knee_angle parameters
                Axis('RKnee'), Axis('RAnkle'),
                Axis('LKnee'), Axis('LAnkle')
            ],

            [
                # ankle_angle parameters
                Axis('RAnkle'), Axis('RFoot'),
                Axis('LAnkle'), Axis('LFoot')
            ],

            [
                # foot_angle parameters
                Measurement('GCS'), Axis('RFoot'),
                Measurement('GCS'), Axis('LFoot')
            ],

            [
                # head_angle parameters
                Measurement('GCS'),
                Axis('Head')
            ],

            [
                # thorax_angle parameters
                Measurement('GCS'),
                Axis('Thorax')
            ],

            [
                # neck_angle parameters
                Axis('Head'),
                Axis('Thorax')
            ],

            [
                # spine_angle parameters
                Axis('Pelvis'),
                Axis('Thorax')
            ],

            [
                # shoulder_angle parameters
                Axis('Thorax'), Axis('RHum'),
                Axis('Thorax'), Axis('LHum')
            ],

            [
                # elbow_angle parameters
                Axis('RHum'), Axis('RRad'),
                Axis('LHum'), Axis('LRad')
            ],

            [
                # wrist_angle parameters
                Axis('RRad'), Axis('RHand'),
                Axis('LRad'), Axis('LHand')
            ]
        ]