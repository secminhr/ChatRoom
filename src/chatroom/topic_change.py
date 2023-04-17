from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional
import copy

from chatroom import logger
if TYPE_CHECKING:
    from chatroom.topic import Topic
'''
Change is a class that represents a change to a topic. It can be serialized and be passed between clients and the server.
When the client wants to change a topic, it creates a Change object and sends it to the server. The server then applies the change to the topic (if it's valid).
The server then sends the change to all the subscribers of the topic.
'''
import uuid

class InvalidChangeError(Exception):
    def __init__(self,topic:Optional[Topic],change:Change,reason:str):
        super().__init__(f'Invalid change {change.serialize()} for topic {topic.get_name() if topic is not None else "unknown"}: {reason}')
        self.topic = topic
        self.change = change
        self.reason = reason

default_topic_value = {
    'string':'',
    'int':0,
    'float':0.0,
    'bool':False,
    'set':[],
    'list':[],
}

def remove_entry(dictionary,key):
    dictionary = dictionary.copy()
    if key in dictionary:
        del dictionary[key]
    return dictionary

def type_validator(t):
    def f(old_value,new_value,change):
        return isinstance(new_value,t)
    return f

class Change: 
    @staticmethod
    def deserialize(change_dict:dict[str,Any])->Change:
        print(change_dict)
        change_type, topic_type, change_dict = change_dict['type'], change_dict['topic_type'], remove_entry(remove_entry(change_dict,'type'),'topic_type')
        return type_name_to_change_types[topic_type].types[change_type](**change_dict)
    
    def __init__(self,topic_name,id:Optional[str]=None):
        self.topic_name = topic_name
        if id is None:
            self.id = str(uuid.uuid4())
        else:
            self.id = id
    def apply(self, old_value):
        return old_value
    def serialize(self):
        raise NotImplementedError()
    def inverse(self)->Change:
        '''
        Inverse() is defined after Apply called. It returns a change that will undo the change.
        '''
        return Change(self.topic_name)

class SetChange(Change):
    def __init__(self,topic_name, value,old_value=None,id=None):
        super().__init__(topic_name,id)
        assert value != [5]
        self.value = value
        self.old_value = old_value
    def apply(self, old_value):
        self.old_value = old_value
        return copy.deepcopy(self.value)
    def inverse(self)->Change:
        return self.__class__(self.topic_name,copy.deepcopy(self.old_value),copy.deepcopy(self.value))
    def serialize(self):
        return {"topic_name":self.topic_name,"topic_type":"unknown","type":"set","value":self.value,"old_value":self.old_value,"id":self.id}

class StringChangeTypes:
    class SetChange(SetChange):
        def serialize(self):
            return {"topic_name":self.topic_name,"topic_type":"string","type":"set","value":self.value,"old_value":self.old_value,"id":self.id}
        
    types = {'set':SetChange}

class SetChangeTypes:
    class SetChange(SetChange):
        def serialize(self):
                return {"topic_name":self.topic_name,"topic_type":"set","type":"set","value":self.value,"old_value":self.old_value,"id":self.id}
    class AppendChange(Change):
        def __init__(self,topic_name, item,id=None):
            super().__init__(topic_name,id)
            self.item = item
        def apply(self, old_value):
            return old_value + [self.item]
        def serialize(self):
            return {"topic_name":self.topic_name,"topic_type":"set","type":"append","item":self.item,"id":self.id}
        def inverse(self)->Change:
            return SetChangeTypes.RemoveChange(self.topic_name,self.item)
        
    class RemoveChange(Change):
        def __init__(self,topic_name, item,id=None):
            super().__init__(topic_name,id)
            self.item = item
        def apply(self, old_value):
            if self.item not in old_value:
                raise InvalidChangeError(None,self,f'Cannot remove {self.item} from {old_value}')
            new_value = old_value[:]
            new_value.remove(self.item)
            return new_value
        def serialize(self):
            return {"topic_name":self.topic_name,"topic_type":"set","type":"remove","item":self.item,"id":self.id}
        def inverse(self)->Change:
            return SetChangeTypes.AppendChange(self.topic_name,self.item)
    
    types = {'set':SetChange,'append':AppendChange,'remove':RemoveChange}

type_name_to_change_types = {'string':StringChangeTypes,'set':SetChangeTypes}