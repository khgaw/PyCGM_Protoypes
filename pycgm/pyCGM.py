import numpy as np
from itertools import chain
import os
import multiprocessing as mp
import sys
import functools
import csv
import static
from pycgm_calc import CalcAxes, CalcAngles
from utils import pycgmIO


class pyCGM():

    class Measurement():
        # a measurement value
        def __init__(self, value):
            self.value = value

    class Marker():
        # a marker slice
        def __init__(self, slice):
            self.slice = slice

    class Axis():
        # an axis index
        def __init__(self, index):
            self.index = index

    class Angle():
        # an angle index
        def __init__(self, index):
            self.index = index

    def __init__(self, measurements, static_trial, dynamic_trial):

        # measurements are a dict, marker data is flat [xyzxyz...] per frame
        self.measurements = static.getStatic(
            static_trial, dict(zip(measurements[0], measurements[1])))
        self.marker_data = np.array(
            [np.asarray(list(frame.values())).flatten() for frame in dynamic_trial])

        # map the list of marker names to slices
        self.marker_keys = dynamic_trial[0].keys()
        self.marker_mapping = {marker_key: slice(
            index*3, index*3+3, 1) for index, marker_key in enumerate(self.marker_keys)}

        # some struct helper attributes
        self.num_frames = len(self.marker_data)
        self.num_axes = len(self.default_axis_keys)
        self.num_axis_floats_per_frame = self.num_axes * 16
        self.axis_results_shape = (self.num_frames, self.num_axes, 4, 4)
        self.num_angles = len(self.default_angle_keys)
        self.num_angle_floats_per_frame = self.num_angles * 3
        self.angle_results_shape = (self.num_frames, self.num_angles, 3)

        # map axes and angles so functions can use results of the current frame
        self.axis_keys = self.default_axis_keys
        self.angle_keys = self.default_angle_keys
        self.axis_mapping = {axis: index for index,
                             axis in enumerate(self.axis_keys)}
        self.angle_mapping = {angle: index for index,
                              angle in enumerate(self.angle_keys)}

        # add non-overridden default pycgm_calc funcs to funcs list
        self.axis_funcs = [func if not hasattr(self, func.__name__) else getattr(
            self, func.__name__) for func in CalcAxes().funcs]
        self.angle_funcs = [func if not hasattr(self, func.__name__) else getattr(
            self, func.__name__) for func in CalcAngles().funcs]

        # map function names to indices
        self.axis_func_mapping = {
            function.__name__: index for index, function in enumerate(self.axis_funcs)}
        self.angle_func_mapping = {
            function.__name__: index for index, function in enumerate(self.angle_funcs)}

        # map function names to the axes they return
        self.axis_result_mapping = {'pelvis_axis': ['Pelvis'],
                                    'hip_joint_center': ['RHipJC', 'LHipJC'],
                                    'hip_axis': ['Hip'],
                                    'knee_axis': ['RKnee', 'LKnee'],
                                    'ankle_axis': ['RAnkle', 'LAnkle'],
                                    'foot_axis': ['RFoot', 'LFoot'],
                                    'head_axis': ['Head'],
                                    'thorax_axis': ['Thorax'],
                                    'wand_marker': ['RWand', 'LWand'],
                                    'clav_joint_center': ['RClavJC', 'LClavJC'],
                                    'clav_axis': ['RClav', 'LClav'],
                                    'hum_axis': ['RHum', 'LHum', 'RWristJC', 'LWristJC'],
                                    'rad_axis': ['RRad', 'LRad'],
                                    'hand_axis': ['RHand', 'LHand']}

        # map function names to the angles they return
        self.angle_result_mapping = {'pelvis_angle': ['Pelvis'],
                                     'hip_angle': ['RHip', 'LHip'],
                                     'knee_angle': ['RKnee', 'LKnee'],
                                     'ankle_angle': ['RAnkle', 'LAnkle'],
                                     'foot_angle': ['RFoot', 'LFoot'],
                                     'head_angle': ['Head'],
                                     'thorax_angle': ['Thorax'],
                                     'neck_angle': ['Neck'],
                                     'spine_angle': ['Spine'],
                                     'shoulder_angle': ['RShoulder', 'LShoulder'],
                                     'elbow_angle': ['RElbow', 'LElbow'],
                                     'wrist_angle': ['RWrist', 'LWrist']}

        # default required slices of axis functions
        self.axis_func_parameters = [
            [
                # pelvis_axis
                self.Marker(self.marker_slice('RASI')),
                self.Marker(self.marker_slice('LASI')),
                self.Marker(self.marker_slice('RPSI')),
                self.Marker(self.marker_slice('LPSI')),
                self.Marker(self.marker_slice('SACR'))
            ],

            [
                # hip_joint_center
                self.Axis(self.axis_index('Pelvis')),
                self.Measurement(self.measurement_value('MeanLegLength')),
                self.Measurement(self.measurement_value(
                    'R_AsisToTrocanterMeasure')),
                self.Measurement(self.measurement_value(
                    'L_AsisToTrocanterMeasure')),
                self.Measurement(self.measurement_value('InterAsisDistance')),
            ],

            [
                # hip_axis
                self.Axis(self.axis_index('RHipJC')),
                self.Axis(self.axis_index('LHipJC')),
                self.Axis(self.axis_index('Pelvis')),
            ],

            [
                # knee_axis
                self.Marker(self.marker_slice('RTHI')),
                self.Marker(self.marker_slice('LTHI')),
                self.Marker(self.marker_slice('RKNE')),
                self.Marker(self.marker_slice('LKNE')),
                self.Axis(self.axis_index('RHipJC')),
                self.Axis(self.axis_index('LHipJC')),
                self.Measurement(self.measurement_value('RightKneeWidth')),
                self.Measurement(self.measurement_value('LeftKneeWidth')),
            ],

            [
                # ankle_axis
                self.Marker(self.marker_slice('RTIB')),
                self.Marker(self.marker_slice('LTIB')),
                self.Marker(self.marker_slice('RANK')),
                self.Marker(self.marker_slice('LANK')),
                self.Axis(self.axis_index('RKnee')),
                self.Axis(self.axis_index('LKnee')),
                self.Measurement(self.measurement_value('RightAnkleWidth')),
                self.Measurement(self.measurement_value('LeftAnkleWidth')),
                self.Measurement(self.measurement_value('RightTibialTorsion')),
                self.Measurement(self.measurement_value('LeftTibialTorsion')),
            ],

            [
                # foot_axis
                self.Marker(self.marker_slice('RTOE')),
                self.Marker(self.marker_slice('LTOE')),
                self.Axis(self.axis_index('RAnkle')),
                self.Axis(self.axis_index('LAnkle')),
                self.Measurement(self.measurement_value('RightStaticRotOff')),
                self.Measurement(self.measurement_value('LeftStaticRotOff')),
                self.Measurement(self.measurement_value(
                    'RightStaticPlantFlex')),
                self.Measurement(self.measurement_value(
                    'LeftStaticPlantFlex')),
            ],

            [
                # head_axis
                self.Marker(self.marker_slice('LFHD')),
                self.Marker(self.marker_slice('RFHD')),
                self.Marker(self.marker_slice('LBHD')),
                self.Marker(self.marker_slice('RBHD')),
            ],

            [
                # thorax_axis
                self.Marker(self.marker_slice('CLAV')),
                self.Marker(self.marker_slice('C7')),
                self.Marker(self.marker_slice('STRN')),
                self.Marker(self.marker_slice('T10')),
            ],

            [
                # wand_marker
                self.Marker(self.marker_slice('RSHO')),
                self.Marker(self.marker_slice('LSHO')),
                self.Axis(self.axis_index('Thorax')),
            ],

            [
                # clav_joint_center/shoulder_joint_center
                self.Marker(self.marker_slice('RSHO')),
                self.Marker(self.marker_slice('LSHO')),
                self.Axis(self.axis_index('Thorax')),
                self.Axis(self.axis_index('RWand')),
                self.Axis(self.axis_index('LWand')),
                self.Measurement(self.measurement_value(
                    'RightShoulderOffset')),
                self.Measurement(self.measurement_value('LeftShoulderOffset')),
            ],


            [
                # clav_axis/shoulder_axis
                self.Axis(self.axis_index('Thorax')),
                self.Axis(self.axis_index('RClavJC')),
                self.Axis(self.axis_index('LClavJC')),
                self.Axis(self.axis_index('RWand')),
                self.Axis(self.axis_index('LWand')),
            ],

            [
                # hum_axis/elbow_joint_center
                self.Marker(self.marker_slice('RELB')),
                self.Marker(self.marker_slice('LELB')),
                self.Marker(self.marker_slice('RWRA')),
                self.Marker(self.marker_slice('RWRB')),
                self.Marker(self.marker_slice('LWRA')),
                self.Marker(self.marker_slice('LWRB')),
                self.Axis(self.axis_index('RClav')),
                self.Axis(self.axis_index('LClav')),
                self.Measurement(self.measurement_value('RightElbowWidth')),
                self.Measurement(self.measurement_value('LeftElbowWidth')),
                self.Measurement(self.measurement_value('RightWristWidth')),
                self.Measurement(self.measurement_value('LeftWristWidth')),
                7.0,  # marker mm
            ],

            [
                # rad_axis/wrist_axis
                self.Axis(self.axis_index('RHum')),
                self.Axis(self.axis_index('LHum')),
                self.Axis(self.axis_index('RWristJC')),
                self.Axis(self.axis_index('LWristJC')),
            ],

            [
                # hand_axis
                self.Marker(self.marker_slice('RWRA')),
                self.Marker(self.marker_slice('RWRB')),
                self.Marker(self.marker_slice('LWRA')),
                self.Marker(self.marker_slice('LWRB')),
                self.Marker(self.marker_slice('RFIN')),
                self.Marker(self.marker_slice('LFIN')),
                self.Axis(self.axis_index('RWristJC')),
                self.Axis(self.axis_index('LWristJC')),
                self.Measurement(self.measurement_value('RightHandThickness')),
                self.Measurement(self.measurement_value('LeftHandThickness'))
            ],
        ]

        self.angle_func_parameters = [

            [
                # pelvis_angle
                self.Measurement(self.measurement_value('GCS')),
                self.Axis(self.axis_index('Pelvis'))
            ],

            [
                # hip_angle
                self.Axis(self.axis_index('Hip')),
                self.Axis(self.axis_index('RKnee')),
                self.Axis(self.axis_index('Hip')),
                self.Axis(self.axis_index('LKnee'))
            ],

            [
                # knee_angle
                self.Axis(self.axis_index('RKnee')),
                self.Axis(self.axis_index('RAnkle')),
                self.Axis(self.axis_index('LKnee')),
                self.Axis(self.axis_index('LAnkle'))
            ],

            [
                # ankle_angle
                self.Axis(self.axis_index('RAnkle')),
                self.Axis(self.axis_index('RFoot')),
                self.Axis(self.axis_index('LAnkle')),
                self.Axis(self.axis_index('LFoot'))
            ],

            [
                # foot_angle
                self.Measurement(self.measurement_value('GCS')),
                self.Axis(self.axis_index('RFoot')),
                self.Measurement(self.measurement_value('GCS')),
                self.Axis(self.axis_index('LFoot'))
            ],

            [
                # head_angle
                self.Measurement(self.measurement_value('GCS')),
                self.Axis(self.axis_index('Head'))
            ],

            [
                # thorax_angle
                self.Measurement(self.measurement_value('GCS')),
                self.Axis(self.axis_index('Thorax'))
            ],

            [
                # neck_angle
                self.Axis(self.axis_index('Head')),
                self.Axis(self.axis_index('Thorax'))
            ],

            [
                # spine_angle
                self.Axis(self.axis_index('Pelvis')),
                self.Axis(self.axis_index('Thorax'))
            ],

            [
                # shoulder_angle
                self.Axis(self.axis_index('Thorax')),
                self.Axis(self.axis_index('RHum')),
                self.Axis(self.axis_index('Thorax')),
                self.Axis(self.axis_index('LHum'))
            ],

            [
                # elbow_angle
                self.Axis(self.axis_index('RHum')),
                self.Axis(self.axis_index('RRad')),
                self.Axis(self.axis_index('LHum')),
                self.Axis(self.axis_index('LRad'))
            ],

            [
                # wrist_angle
                self.Axis(self.axis_index('RRad')),
                self.Axis(self.axis_index('RHand')),
                self.Axis(self.axis_index('LRad')),
                self.Axis(self.axis_index('LHand'))
            ]
        ]

    def marker_slice(self, marker_name):
        # retrieve the slice that corresponds to the given marker name

        return self.marker_mapping[marker_name] if marker_name in self.marker_mapping.keys() else None

    def measurement_value(self, measurement_name):
        # retrieve the value of the given measurement name

        return self.measurements[measurement_name] if measurement_name in self.measurements.keys() else None

    def axis_index(self, axis_name):
        # retrieve the axis results index of the given axis name

        return self.axis_mapping[axis_name] if axis_name in self.axis_mapping.keys() else None

    def angle_index(self, angle_name):
        # retrieve the angle results index of the given angle name

        return self.angle_mapping[angle_name] if angle_name in self.angle_mapping.keys() else None

    def modify_function(self, function, markers=None, measurements=None, axes=None, angles=None, returns_axes=None, returns_angles=None):
        # modify an existing function's parameters and returned values
        # used for overriding an existing function's parameters or returned results

        if returns_axes is not None and returns_angles is not None:
            sys.exit(
                '{} must return either an axis or an angle, not both'.format(function))

        # get parameters
        params = []
        for marker_name in [marker_name for marker_name in (markers or [])]:
            params.append(self.Marker(self.marker_slice(marker_name)))
        for measurement_name in [measurement_name for measurement_name in (measurements or [])]:
            params.append(self.Measurement(
                self.measurement_value(measurement_name)))
        for axis_name in [axis_name for axis_name in (axes or [])]:
            params.append(self.Axis(self.axis_index(axis_name)))
        for angle_name in [angle_name for angle_name in (angles or [])]:
            params.append(self.Angle(self.angle_index(angle_name)))

        if isinstance(function, str):  # make sure a function name is passed
            if function in self.axis_func_mapping:
                self.axis_funcs[self.axis_func_mapping[function]
                                ] = getattr(self, function)
                self.axis_func_parameters[self.axis_func_mapping[function]] = params
            elif function in self.angle_func_mapping:
                self.angle_funcs[self.angle_func_mapping[function]] = getattr(
                    self, function)
                self.angle_func_parameters[self.angle_func_mapping[function]] = params
            else:
                sys.exit('Function {} not found'.format(function))
        else:
            sys.exit('Pass the name of the function as a string like so: \'{}\''.format(
                function.__name__))

        # add returned axes, update
        if returns_axes is not None:
            self.axis_result_mapping[function] = returns_axes
            self.num_axes = len(
                list(chain(*self.axis_result_mapping.values())))
            self.axis_mapping = {axis_name: index for index,
                                 axis_name in enumerate(self.axis_keys)}
            self.num_axis_floats_per_frame = self.num_axes * 16
            self.axis_results_shape = (self.num_frames, self.num_axes, 4, 4)

        # add returned angles, update
        if returns_angles is not None:
            self.angle_result_mapping[function] = returns_angles
            self.num_angles = len(
                list(chain(*self.angle_result_mapping.values())))
            self.angle_mapping = {angle_name: index for index,
                                  angle_name in enumerate(self.angle_keys)}
            self.num_angle_floats_per_frame = self.num_angles * 3
            self.angle_results_shape = (self.num_frames, self.num_angles, 3)

    def add_function(self, function, markers=None, measurements=None, axes=None, angles=None, returns_axes=None, returns_angles=None):
        # add a custom function to pycgm

        # get func object and name
        if isinstance(function, str):
            func_name = function
            func = getattr(self, func_name)
        elif callable(function):
            func_name = function.__name__
            func = function

        if returns_axes is not None and returns_angles is not None:
            sys.exit(
                '{} must return either an axis or an angle, not both'.format(func_name))
        if returns_axes is None and returns_angles is None:
            sys.exit('{} must return a custom axis or angle. if the axis or angle already exists by default, just use self.modify_function()'.format(func_name))

        # get parameters
        params = []
        for marker_name in [marker_name for marker_name in (markers or [])]:
            params.append(self.Marker(self.marker_slice(marker_name)))
        for measurement_name in [measurement_name for measurement_name in (measurements or [])]:
            params.append(self.Measurement(
                self.measurement_value(measurement_name)))
        for axis_name in [axis_name for axis_name in (axes or [])]:
            params.append(self.Axis(self.axis_index(axis_name)))
        for angle_name in [angle_name for angle_name in (angles or [])]:
            params.append(self.Angle(self.angle_index(angle_name)))

        if returns_axes is not None:  # extend axes and update
            self.axis_funcs.append(func)
            self.axis_func_mapping = {
                function.__name__: index for index, function in enumerate(self.axis_funcs)}
            self.axis_func_parameters.append([])
            self.axis_result_mapping[function] = returns_axes
            self.axis_keys.extend(returns_axes)
            self.num_axes = len(
                list(chain(*self.axis_result_mapping.values())))
            self.axis_mapping = {axis_name: index for index,
                                 axis_name in enumerate(self.axis_keys)}
            self.num_axis_floats_per_frame = self.num_axes * 16
            self.axis_results_shape = (self.num_frames, self.num_axes, 4, 4)

            # set parameters of new function
            self.axis_func_parameters[self.axis_func_mapping[func_name]] = params

        if returns_angles is not None:  # extend angles and update
            self.angle_funcs.append(func)
            self.angle_func_mapping = {
                function.__name__: index for index, function in enumerate(self.angle_funcs)}
            self.angle_func_parameters.append([])
            self.angle_result_mapping[function] = returns_angles
            self.angle_keys.extend(returns_angles)
            self.num_angles = len(
                list(chain(*self.angle_result_mapping.values())))
            self.angle_mapping = {angle_name: index for index,
                                  angle_name in enumerate(self.angle_keys)}
            self.num_angle_floats_per_frame = self.num_angles * 3
            self.angle_results_shape = (self.num_frames, self.num_angles, 3)

            # set parameters of new function
            self.angle_func_parameters[self.angle_func_mapping[func_name]] = params

    @property
    def default_angle_keys(self):
        # list of default angle result names

        return ['Pelvis', 'RHip', 'LHip', 'RKnee', 'LKnee', 'RAnkle',
                'LAnkle', 'RFoot', 'LFoot',
                'Head', 'Thorax', 'Neck', 'Spine', 'RShoulder', 'LShoulder',
                'RElbow', 'LElbow', 'RWrist', 'LWrist']

    @property
    def default_axis_keys(self):
        # list of default axis result names

        return ['Pelvis', 'RHipJC', 'LHipJC', 'Hip', 'RKnee', 'LKnee', 'RAnkle', 'LAnkle', 'RFoot', 'LFoot', 'Head',
                'Thorax', 'RWand', 'LWand', 'RClavJC', 'LClavJC', 'RClav', 'LClav', 'RHum', 'LHum', 'RWristJC', 'LWristJC', 'RRad', 'LRad', 'RHand', 'LHand']

    def check_robo_results_accuracy(self, axis_results):
        # test structured axes against existing csv output file
        # this will be removed later

        csv_fields = ["PELO", "PELX", "PELY", "PELZ", "HIPO", "HIPX", "HIPY", "HIPZ",
                      "R KNEO", "R KNEX", "R KNEY", "R KNEZ", "L KNEO", "L KNEX", "L KNEY", "L KNEZ",
                      "R ANKO", "R ANKX", "R ANKY", "R ANKZ", "L ANKO", "L ANKX", "L ANKY", "L ANKZ",
                      "R FOOO", "R FOOX", "R FOOY", "R FOOZ", "L FOOO", "L FOOX", "L FOOY", "L FOOZ",
                      "HEAO", "HEAX", "HEAY", "HEAZ", "THOO", "THOX", "THOY", "THOZ", "R CLAO", "R CLAX",
                      "R CLAY", "R CLAZ", "L CLAO", "L CLAX", "L CLAY", "L CLAZ", "R HUMO", "R HUMX",
                      "R HUMY", "R HUMZ", "L HUMO", "L HUMX", "L HUMY", "L HUMZ", "R RADO", "R RADX",
                      "R RADY", "R RADZ", "L RADO", "L RADX", "L RADY", "L RADZ", "R HANO", "R HANX",
                      "R HANY", "R HANZ", "L HANO", "L HANX", "L HANY", "L HANZ"]

        axis_array_fields = ['Pelvis', 'Hip', 'RKnee', 'LKnee', 'RAnkle', 'LAnkle', 'RFoot', 'LFoot', 'Head',
                             'Thorax', 'RClav', 'LClav', 'RHum', 'LHum', 'RRad', 'LRad', 'RHand', 'LHand']

        slice_map = {key: slice(index*12, index*12+12, 1)
                     for index, key in enumerate(axis_array_fields)}

        missing_axes = ['RClav', 'LClav', 'RFoot', 'LFoot', 'Head']
        accurate = True

        actual_results = np.genfromtxt(
            'SampleData/Sample_2/RoboResults_pycgm.csv', delimiter=',')
        for frame_idx, frame in enumerate(actual_results):
            frame = frame[58:]
            for key, slc in slice_map.items():
                if any(missing_axis in key for missing_axis in missing_axes):
                    continue

                original_o = frame[slc.start:slc.start + 3]
                original_x = frame[slc.start + 3:slc.start + 6]
                original_y = frame[slc.start + 6:slc.start + 9]
                original_z = frame[slc.start + 9:slc.stop]
                refactored_o = axis_results[frame_idx][key][:3, 3]
                refactored_x = axis_results[frame_idx][key][0,
                                                            :3] + refactored_o
                refactored_y = axis_results[frame_idx][key][1,
                                                            :3] + refactored_o
                refactored_z = axis_results[frame_idx][key][2,
                                                            :3] + refactored_o
                if not np.allclose(original_o, refactored_o, rtol=1.e-3, atol=1e-2):
                    accurate = False
                    print(f'{frame_idx}: {key}, origin')
                if not np.allclose(original_x, refactored_x, rtol=1.e-3, atol=1.e-2):
                    accurate = False
                    print(f'{frame_idx}: {key}, x-axis')
                if not np.allclose(original_y, refactored_y, rtol=1.e-3, atol=1.e-2):
                    accurate = False
                    print(f'{frame_idx}: {key}, y-axis')
                if not np.allclose(original_z, refactored_z, rtol=1.e-3, atol=1.e-2):
                    accurate = False
                    print(f'{frame_idx}: {key}, z-axis')
        print(
            'All results, not including missing axes, in line with roboresults?', accurate)

    def structure_trial_axes(self, axis_results):
        # takes a flat array of floats that represent the 4x4 axes at each frame
        # returns a structured array, indexed by result[optional frame slice or index][axis name]

        axis_result_keys = list(chain(*self.axis_result_mapping.values()))
        axis_row_dtype = np.dtype([(key, 'f8', (4, 4))
                                  for key in axis_result_keys])

        return np.array([tuple(frame) for frame in axis_results.reshape(self.axis_results_shape)], dtype=axis_row_dtype)

    def structure_trial_angles(self, angle_results):
        # takes a flat array of floats that represent the 3x1 angles at each frame
        # returns a structured array, indexed by result[optional frame slice or index][angle name]

        angle_result_keys = list(chain(*self.angle_result_mapping.values()))
        angle_row_dtype = np.dtype([(key, 'f8', (3,))
                                   for key in angle_result_keys])

        return np.array([tuple(frame) for frame in angle_results.reshape(self.angle_results_shape)], dtype=angle_row_dtype)

    def multi_run(self, cores=None):
        # parallelize on blocks of frames

        flat_rows = self.marker_data

        # create a shared array to store axis and angle results
        shared_axes = mp.RawArray('d', self.num_frames * self.num_axes * 16)
        shared_angles = mp.RawArray('d', self.num_frames * self.num_angles * 3)
        nprocs = cores if cores is not None else os.cpu_count() - 1
        marker_data_blocks = np.array_split(flat_rows, nprocs)

        processes = []
        frame_index_offset = 0
        for i in range(nprocs):
            frame_count = len(marker_data_blocks[i])

            processes.append(mp.Process(target=self.run,
                                        args=(marker_data_blocks[i],
                                              frame_index_offset,
                                              frame_index_offset + frame_count,
                                              self.num_axis_floats_per_frame,
                                              self.num_angle_floats_per_frame,
                                              shared_axes,
                                              shared_angles),
                                        daemon=True))

            processes[i].start()
            frame_index_offset += frame_count

        for process in processes:
            process.join()

        # structure flat axis and angle results
        self.axes = self.structure_trial_axes(
            np.frombuffer(shared_axes, dtype=np.float64))
        self.angles = self.structure_trial_angles(
            np.frombuffer(shared_angles, dtype=np.float64))

    def run(self, frames=None, index_offset=None, index_end=None, axis_results_size=None, angle_results_size=None, shared_axes=None, shared_angles=None):

        flat_axis_results = np.array([], dtype=np.float64)
        flat_angle_results = np.array([], dtype=np.float64)

        if shared_angles is not None:  # multiprocessing, write to shared memory
            shared_axes = np.frombuffer(shared_axes, dtype=np.float64)
            shared_angles = np.frombuffer(shared_angles, dtype=np.float64)

            for frame in frames:
                flat_axis_results = np.append(
                    flat_axis_results,
                    self.calc(frame)[0].flatten()
                )
                flat_angle_results = np.append(
                    flat_angle_results, self.calc(frame)[1].flatten())

            shared_axes[index_offset * axis_results_size: index_end *
                        axis_results_size] = flat_axis_results
            shared_angles[index_offset * angle_results_size: index_end *
                          angle_results_size] = flat_angle_results

        else:  # single core, just calculate and structure
            for frame in self.marker_data:
                flat_axis_results = np.append(
                    flat_axis_results,
                    self.calc(frame)[0].flatten()
                )
                flat_angle_results = np.append(
                    flat_angle_results, self.calc(frame)[1].flatten())

            # structure flat axis and angle results
            self.axes = self.structure_trial_axes(flat_axis_results)
            self.angles = self.structure_trial_angles(flat_angle_results)

    def calc(self, frame):
        axis_results = []
        angle_results = []

        # run axis functions in sequence
        for index, func in enumerate(self.axis_funcs):
            axis_params = []

            for i, param in enumerate(self.axis_func_parameters[index]):
                if isinstance(param, self.Marker):  # marker data slice
                    axis_params.append(frame[param.slice])
                elif isinstance(param, self.Measurement):  # measurement value
                    axis_params.append(param.value)
                elif isinstance(param, self.Axis):  # axis mapping index
                    axis_params.append(axis_results[param.index])
                else:
                    axis_params.append(param)

            ret_axes = np.asarray(func(*axis_params))

            if ret_axes.ndim == 3:  # multiple axes returned by one function
                for axis in ret_axes:
                    axis_results.append(axis)
            else:
                axis_results.append(ret_axes)

        # run angle functions in sequence
        for index, func in enumerate(self.angle_funcs):
            angle_params = []

            for param in self.angle_func_parameters[index]:
                if isinstance(param, self.Marker):  # marker data slice
                    angle_params.append(frame[param.slice])
                elif isinstance(param, self.Measurement):  # measurement value
                    angle_params.append(param.value)
                elif isinstance(param, self.Axis):  # axis mapping index
                    angle_params.append(axis_results[param.index])
                else:
                    angle_params.append(param)

            ret_angles = np.asarray(func(*angle_params))

            if ret_angles.ndim == 2:  # multiple angles returned by one function
                for angle in ret_angles:
                    angle_results.append(angle)
            else:
                angle_results.append(ret_angles)

        return [np.asarray(axis_results), np.asarray(angle_results)]
