import numpy as np
import os
import multiprocessing as mp
import sys
import functools
import csv

sys.path.append("..")
from utils import pycgmIO

def parameters(*args):
    # decorator parameters are keys
    # finds key in either the marker data or the measurement data
    # sets function parameters accordingly
    def decorator(func):
        params = list(args)

        @functools.wraps(func)
        def set_required_markers(*args):
            self = args[0]
            func_index = self.func_mapping[func.__name__]

            if func in self.funcs_already_known:
                pass
            else: # find and add parameters only once per function per process
                self.func_slices[func_index] = [self.find(param) for param in params]
                self.funcs_already_known.append(func)

            return func(*list(map(lambda req_slice:  self.marker_data[self.current_frame][req_slice] if isinstance(req_slice, slice) else req_slice, self.func_slices[func_index])))
        return set_required_markers
    return decorator

def customfunc(*args):
    # decorator parameters are keys
    # finds key in either the marker data or the measurement data
    # sets function parameters accordingly
    def decorator(func):
        params = list(args)
        test = func
        print('test1')

        @functools.wraps(func)
        def wrapped(self, **args):
            test2 = self
            test3 = list(args)
            print('test2')
    
        # self.funcs.append(func)
        # self.func_mapping = {function.__name__: index for index, function in enumerate(self.funcs)}
        print('decorator called')

    return decorator

class pyCGM():

    # TODO extensibility, more subject manager helper funcs (add 1 subject with 15 trials, etc.) 

    def __init__(self, measurements, markers):

        # marker data is flattened [xyzxyz...] per frame
        self.measurements = dict(zip(measurements[0], measurements[1]))
        self.marker_data = np.array([np.array(list(frame.values())).flatten() for frame in markers])

        # list of marker names
        self.marker_keys = markers[0].keys()
        self.marker_mapping = {marker_key: slice(index*3, index*3+3, 1) for index, marker_key in enumerate(self.marker_keys)}

        # some struct helper attributes
        self.num_frames = len(self.marker_data)
        self.num_axes = len(self.axis_result_keys)
        self.num_floats_per_frame = self.num_axes * 16
        self.axis_results_shape = (self.num_frames, self.num_axes, 4, 4)

        # store these for later extension
        self.axis_keys = self.axis_result_keys
        self.angle_keys = self.angle_result_keys

        # list of functions and their parameters
        self.current_frame = 0
        self.funcs = [self.pelvis_axis]
        self.funcs_already_known = []
        self.func_mapping = {function.__name__: index for index, function in enumerate(self.funcs)}
        self.func_slices = [
                                [
                                    # pelvis_axis 
                                    self.marker_mapping['RASI'],
                                    self.marker_mapping['LASI'],
                                    self.marker_mapping['RPSI'],
                                    self.marker_mapping['LPSI'],
                                    self.marker_mapping['SACR'] if 'SACR' in self.marker_mapping.keys() else None
                                ]
                            ]

    def add_function(self, name, axes=None, angles=None):

        # get func object
        func = getattr(self, name)

        # append to func list, update mapping, add empty slices entry
        self.funcs.append(func)
        self.func_mapping = {function.__name__: index for index, function in enumerate(self.funcs)}
        self.func_slices.append([])

        # add axes and angles
        if axes is not None:
            self.axis_keys.extend(axes)
        if angles is not None:
            self.angle_keys.extend(angles)

        # update
        self.num_axes = len(self.axis_keys)
        self.num_floats_per_frame = self.num_axes * 16
        self.axis_results_shape = (self.num_frames, self.num_axes, 4, 4)

        self.funcs_added = True


    @property
    def angle_result_keys(self):
        # list of angle result names (currently not used)

        return ['Pelvis', 'R Hip', 'L Hip', 'R Knee', 'L Knee', 'R Ankle',
                'L Ankle', 'R Foot', 'L Foot',
                'Head', 'Thorax', 'Neck', 'Spine', 'R Shoulder', 'L Shoulder',
                'R Elbow', 'L Elbow', 'R Wrist', 'L Wrist']

    @property
    def axis_result_keys(self):
        # list of axis result names

        return ['Pelvis', 'Hip', 'Knee', 'Ankle', 'Foot', 'Head', 'Thorax', 'RClav',
                'LClav', 'RHum', 'LHum', 'RRad', 'LRad', 'RHand', 'LHand']

    def find(self, key):
        value = None
        try:
            value = self.marker_mapping[key]
        except KeyError:
            try:
                value = self.measurements[key]
            except KeyError:
                pass
        return value

    def check_robo_results_accuracy(self, axis_results):
        # test unstructured pelvis axes against existing csv output file

        actual_results = np.genfromtxt('../SampleData/Sample_2/RoboResults_pycgm.csv', delimiter=',')
        pelvis_OXYZ = [row[58:70] for row in actual_results]
        accurate = True
        for i, frame in enumerate(pelvis_OXYZ):
            if not np.allclose(frame[:3], axis_results[i][0][:3,3]):
                accurate = False
            if not np.allclose(frame[3:6], axis_results[i][0][0, :3]):
                accurate = False
            if not np.allclose(frame[6:9], axis_results[i][0][1, :3]):
                accurate = False
            if not np.allclose(frame[9:12], axis_results[i][0][2, :3]):
                accurate = False
        print('All pelvis results in line with RoboResults_pycgm.csv: ', accurate)

    def structure_trial_axes(self, axis_results):
        # takes a flat array of floats that represent the 4x4 axes at each frames
        # returns a structured array, indexed by result[optional frame slice or index][axis name]

        axis_results = axis_results.reshape(self.axis_results_shape)

        # self.check_robo_results_accuracy(axis_results) # uncomment to check accuracy

        axis_row_dtype = np.dtype([(name, 'f4', (4, 4)) for name in self.axis_keys])
        axis_data_dtype = np.dtype((axis_row_dtype))

        structured_axis_results = np.empty([self.num_frames], dtype=axis_data_dtype)

        for i in range(self.num_frames):
            structured_axis_results[i] = np.asarray(tuple(axis_results[i]), dtype=axis_row_dtype)

        return structured_axis_results

    def multi_run(self, cores=None):
        # parallelize on blocks of frames 

        flat_rows = self.marker_data

        # create a shared array to store axis results
        shared_axes = mp.RawArray('f', self.num_frames * self.num_axes * 16)
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
                                              self.num_floats_per_frame,
                                              shared_axes)))

            frame_index_offset += frame_count

        for process in processes:
            process.start()
        for process in processes:
            process.join()

        # structure flat result array
        self.result = self.structure_trial_axes(np.frombuffer(shared_axes, dtype=np.float32))

    def run(self, frames=None, index_offset=None, index_end=None, frame_result_size=None, shared_axes=None):

        flat_results = np.array([], dtype=np.float32)

        if shared_axes is not None:  # multiprocessing, write to shared memory
            shared_array = np.frombuffer(shared_axes, dtype=np.float32)
            self.current_frame = index_offset

            for index, frame in enumerate(frames):
                flat_results = np.append(flat_results, self.calc(frame).flatten())
                self.current_frame += 1

            shared_array[index_offset * frame_result_size: index_end * frame_result_size] = flat_results

        else:  # single core, just calculate and structure
            for index, frame in enumerate(self.marker_data):
                flat_results = np.append(flat_results, self.calc(frame).flatten())

            # structure flat result array
            self.result = self.structure_trial_axes(flat_results)

    def calc(self, frame):
        results = []
        for index, func in enumerate(self.funcs):
            # 'pelvis_axis = ...' will become 'results = np.append(results, ...)' when all funcs are implemented
            result = func(*list(map(lambda req_slice:  frame[req_slice] if isinstance(req_slice, slice) else req_slice, self.func_slices[index])))
            
        for i in range(self.num_axes): # there's only one calculation here, but results should take the shape of all axis results
            results = np.append(results, result)
        return results

    def pelvis_axis(self, rasi, lasi, rpsi, lpsi, sacr=None):
        # get the refactored 4x4 pelvis axis

        if rpsi is not None and lpsi is not None:
            sacrum = (rpsi + lpsi)/2.0
        else:
            sacrum = sacr

        origin = (rasi+lasi)/2.0
        beta1 = origin - sacrum
        beta2 = lasi - rasi
        y_axis = beta2 / np.linalg.norm(beta2)
        beta3_cal = np.dot(beta1, y_axis)
        beta3_cal2 = beta3_cal * y_axis
        beta3 = beta1-beta3_cal2
        x_axis = beta3/np.linalg.norm(beta3)
        z_axis = np.cross(x_axis, y_axis)

        # I added these back to check for correctness
        y_axis = y_axis+origin
        z_axis = z_axis+origin
        x_axis = x_axis+origin

        pelvis = np.zeros((4, 4))
        pelvis[3, 3] = 1.0
        pelvis[0, :3] = x_axis
        pelvis[1, :3] = y_axis
        pelvis[2, :3] = z_axis
        pelvis[:3, 3] = origin

        return pelvis

    class SubjectManager():

        def __init__(self, list_of_subjects):
            self.subject_list = list_of_subjects

        def multi_run(self):
            # parallelize on trials

            # get the total number of floats in all trials for the flat shared buffer
            num_frames = 0
            num_axes = 0
            for subject in self.subject_list:
                num_frames += subject.num_frames
                num_axes += subject.num_axes

            # create a shared array of all subjects' results
            shared_axes = mp.RawArray('f', num_frames * num_axes * 15)

            nprocs = os.cpu_count() - 1
            split_subjects_by_core = np.array_split(np.asarray(self.subject_list), nprocs)

            processes = []
            start_offset = 0
            for i in range(nprocs):
                core_float_count = np.sum([np.prod(subject.axis_results_shape) for subject in split_subjects_by_core[i]])
                processes.append(mp.Process(
                    target=self.run_core_subjects,
                    args=(split_subjects_by_core,
                          i,
                          shared_axes,
                          start_offset,
                          start_offset + core_float_count)))

                start_offset += core_float_count

            for process in processes:
                process.start()
            for process in processes:
                process.join()

            # reconstruct per-subject results and set values of objects in main process
            floats_offset = 0
            for subject in self.subject_list:
                floats_count = np.prod((subject.axis_results_shape))
                subject.result = subject.structure_trial_axes(np.asarray(shared_axes[floats_offset:floats_offset + floats_count]))
                floats_offset += floats_count

        def run_core_subjects(self, split_subjects_by_core, core_index, shared_axes, start_index, end_index):
            # if more subjects than cores, each core may end up running more than one subject
            # cores will run their respective subjects and write their flattened results to the results buffer

            shared_array = np.frombuffer(shared_axes, dtype=np.float32)
            floats = []
            for subject in split_subjects_by_core[core_index]:
               subject.run()
               floats.append(np.array([[frame[i].flatten()] for i in range(subject.num_axes) for frame in subject.result]).flatten())
            shared_array[start_index:end_index] = np.asarray(floats).flatten()

        def joint_axis(self, key, start=None, end=None):
            # get specific joint axis of all subjects at optional frame index or slice

            return [subject.result[start:end][key] for subject in self.subject_list]

class harrington_pelvis_jc_CGM(pyCGM):

    @parameters('InterAsisDistance', 'InterPsisDistance' 'LegLength')
    # dataset has no PelvisDepth or 
    def pelvis_axis(pelvis_width, pel):
        # get the refactored 4x4 pelvis axis

        pelvis = np.zeros((4, 4))
        pelvis[3, 3] = 1.0
        pelvis[0, :3] = x_axis
        pelvis[1, :3] = y_axis
        pelvis[2, :3] = z_axis
        pelvis[:3, 3] = origin

        return pelvis

class oxfordCGM(pyCGM):

    @parameters('RANK', 'RCPG', 'RSTL', 'RHLX', 'RLCA', 'RHEE', 'RP1M', 'RP5M', 'RD5M',' RTOE')
    def oxford_foot(rank, rcpg, rstl, rhlx, rlca, rhee, rp1m, rp5m, rd5m, rtoe):
        '''
        returns:
        LFFHFA/RFFHFA: L/R forefoot with respect to hindfoot
        LFFTBA/RFFTBA: L/R forefoot with respect to tibia
        LHFTBA/RHFTBA: L/R hindfoot with respect to tibia
        LHXFFA/RHXFFA: L/R hallux with respect to forefoot
        '''

        # print('Oxford called with:')
        # print('rank', rank, 'rcpg', rcpg,
        #       'rstl', rstl, 'rhlx', rhlx,
        #       'rlca', rlca, 'rhee', rhee,
        #       'rp1m', rp1m, 'rp5m', rp5m,
        #       'rd5m', rd5m, 'rtoe', rtoe)
        return np.zeros((4,4))


measurements = pycgmIO.loadVSK('../SampleData/Sample_2/RoboSM.vsk')
# marker_data = pycgmIO.loadData('../SampleData/Sample_2/RoboWalk.c3d')
oxford_marker_data = pycgmIO.loadData('../SampleData/Oxford/OFM_Walk1.c3d')

# matt = custom_pelvis_CGM(measurements, marker_data)
# steve = pyCGM(measurements, marker_data)
# bob = pyCGM(measurements, marker_data)

# # running one subject, giving each core a block of frames to calculate
# matt.multi_run()
# matt_pelvis = matt.result['Pelvis'] # matt's pelvis axis at each frame
# matt_pelvis_frame_400 = matt.result[400]['Pelvis'] # matt's pelvis axis at frame 400

# # # run 18 subjects, giving each core a list of subjects to calculate
# subjects = pyCGM.SubjectManager([matt, steve, bob, matt, steve, bob, matt, steve, bob, matt, steve, bob, matt, steve, bob, matt, steve, bob])
# subjects.multi_run()
# all_pelvis = subjects.joint_axis('Pelvis') # pelvis axes of all subjects, all frames
# pelvis_frames_5_15 = subjects.joint_axis('Pelvis', 5, 15) # pelvis axes of all subjects, frames 5-15

oxford_matt = oxfordCGM(measurements, oxford_marker_data)
oxford_matt.add_function('oxford_foot', axes=['fake', 'axes'])
oxford_matt.multi_run()
test = oxford_matt.result['fake']
sys.exit()
