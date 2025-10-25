import json


def map_and_copy(source, destination):
    for attr in vars(destination):
        if hasattr(source, attr):
            setattr(destination, attr, getattr(source, attr))

    return destination


def serialize(obj):
    serialized_obj = ""
    if isinstance(obj, list):
        serialized_obj = [serialize(item) for item in obj]
    elif isinstance(obj, dict):
        serialized_obj =  {k: serialize(v) for k, v in obj.items()}
    elif hasattr(obj, "to_dict"):
        serialized_obj =  obj.to_dict()
    elif hasattr(obj, "__dict__"):
        serialized_obj =  obj.__dict__
    else:
        return obj

    serialized_obj = json.dumps(serialized_obj)
    return serialized_obj