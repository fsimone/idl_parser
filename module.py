import os, sys, traceback

from . import node, type, exception
from . import interface
global_namespace = '__global__'
sep = '::'

class IDLModule(node.IDLNode):

    def __init__(self, name=None, parent = None):
        super(IDLModule, self).__init__('IDLModule', name, parent)
        self._verbose = False
        if name is None:
            self._name = global_namespace
            
        self._interfaces = []
        self._modules = []

    @property
    def is_global(self):
        return self.name == global_namespace
        
    @property
    def full_path(self):
        if self.parent is None:
            return '' # self.name
        else:
            if len(self.parent.full_path) == 0:
                return self.name
            return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False):
        dic = {'module %s' % self.name : [i.to_simple_dic(quiet) for i in self.interfaces] +
               [m.to_simple_dic(quiet) for m in self.modules]}
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath, 
                'classname' : self.classname,
                'interfaces' : [i.to_dic() for i in self.interfaces],
                'modules' : [m.to_dic() for m in self.modules]}
        return dic
    

    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath
        if not self.name == global_namespace:
            brace = token_buf.pop()
            if not brace == '{':
                if self._verbose: sys.stdout.write('# Error. No brace "{".\n')
                raise exception.InvalidIDLSyntaxError()

        while True:
            token = token_buf.pop()
            if token == None:
                if self.name == global_namespace:
                    break
                if self._verbose: sys.stdout.write('# Error. No brace "}".\n')
                raise exception.InvalidIDLSyntaxError()
            elif token == 'module':
                name_ = token_buf.pop()
                m = self.module_by_name(name_)
                if m == None:
                    m = IDLModule(name_, self)
                    self._modules.append(m)
                m.parse_tokens(token_buf, filepath=filepath)
                
            elif token == 'interface':
                name_ = token_buf.pop()
                i = self.interface_by_name(name_)
                if i == None:
                    i = interface.IDLInterface(name_, self)
                    self._interfaces.append(i)
                i.parse_tokens(token_buf, filepath=filepath)

                
            elif token == '}':
                token = token_buf.pop()
                if not token == ';':
                    if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                    raise exception.InvalidIDLSyntaxError()
                break
            
        return True



    @property
    def modules(self):
        return self._modules

    def module_by_name(self, name):
        for m in self.modules:
            if m.name == name:
                return m
        return None

    def for_each_module(self, func):
        retval = []
        for m in self.modules:
            retval.append(func(m))
        return retval

    @property
    def interfaces(self):
        return self._interfaces

    def interface_by_name(self, name):
        for i in self.interfaces:
            if i.name == name:
                return i
        return None

    def for_each_interface(self, func):
        retval = []
        for m in self.interfaces:
            retval.append(func(m))            
        return retval

    def find_types(self, full_typename):
        if type.is_primitive(full_typename):
            return [type.IDLType(full_typename, self)]
        typenode = []

        def parse_node(s, name=str(full_typename)):
            if s.name == name.strip() or s.full_path == name.strip():
                typenode.append(s)

        def parse_function(m):
            typefull = m.find_types(full_typename)
            if (typefull.__len__() > 0):
                typenode.append(typefull)
                
                
        def parse_module(m):
            m.for_each_module(parse_module)
            #m.for_each_struct(parse_node)
            #m.for_each_typedef(parse_node)
            #m.for_each_enum(parse_node)
            #m.for_each_interface(parse_node)
            m.for_each_interface(parse_function)


        parse_module(self)

        return typenode


    