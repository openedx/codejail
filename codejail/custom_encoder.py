import json


class GlobalEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj).__module__ == 'numpy':
            return NumpyEncoder().default(obj)
        elif type(obj).__module__ == 'pandas':
            if hasattr(obj, 'to_json'):
                return obj.to_json(orient='records')
            return repr(obj)
        return json.JSONEncoder.default(self, obj)


class NumpyEncoder(json.JSONEncoder):
    """ Custom encoder for numpy data types """

    def default(self, obj):
        import numpy as np
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.complex_, np.complex64, np.complex128)):
            return {'real': obj.real, 'imag': obj.imag}
        elif isinstance(obj, (np.ndarray)):
            return obj.tolist()
        elif isinstance(obj, (np.bool_)):
            return bool(obj)
        return repr(obj)
