import os, sys, traceback

from . import node, union, exception
from . import type as idl_type


class IDLMember(node.IDLNode):
    def __init__(self, parent):
        super(IDLMember, self).__init__('IDLMember', '', parent)
        self._verbose = True
        self._type = None
        self._annotation = ''
        self.sep = '::'
    
    @property
    def full_path(self):
        return self.parent.full_path + self.sep + self.name

    def parse_blocks(self, blocks, filepath=None):
        self._filepath = filepath
        name, typ, ann = self._name_and_type(blocks)
        if name.find('[') >= 0:
            name_ = name[:name.find('[')]
            arraysize_ = name[name.find('['):]
            #typ = type_.name.strip() + name[name.find('['):]
            name = name_ + arraysize_
        self._name = name
        self._annotation = ann
        self._type = idl_type.IDLType(typ, self)

    def to_simple_dic(self, recursive=False, member_only=False):
        if recursive:
            if self.type.is_primitive:
                return str(self.type) + ' ' + self.name
            elif self.type.obj.is_enum:
                return str('enum') + ' ' + self.name
            dic = {str(self.type) +' ' + self.name : 
                   self.type.obj.to_simple_dic(recursive=recursive, member_only=True)}
            return dic
        dic = {self.name : str(self.type) }
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath, 
                'classname' : self.classname,
                'type' : str(self.type) }
        return dic

    @property
    def type(self):
        if self._type.classname == 'IDLBasicType': # Struct
            typs = self.root_node.find_types(self._type.name)
            if len(typs) == 0:
                print('-- Can not find Data Type (%s)\n' % self._type.name)
                #raise exception.InvalidDataTypeException(self._type.name)
            #return typs[0]
        return self._type
    
    @type.setter
    def type(self, value):
        self._type = value
    

    def get_type(self, extract_typedef=False):
        if extract_typedef:
            if self.type.is_typedef:
                return self.type.type
        return self.type
    

    def post_process(self):
        #self._type = self.refine_typename(self.type)
        pass
      
    
    @property
    def annotation(self):
        return self._annotation
              

class IDLStruct(node.IDLNode):
    
    def __init__(self, name, parent):
        super(IDLStruct, self).__init__('IDLStruct', name.strip(), parent)
        self._verbose = True
        self._members = []
        self.sep = '::'
        
    @property
    def full_path(self):
        return (self.parent.full_path + self.sep + self.name).strip()

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        name = self.full_path if full_path else self.name
        if quiet:
            return 'struct %s' % name 
        
        dic = { 'struct %s' % name : [v.to_simple_dic(recursive=recursive) for v in self.members] }

        if member_only:
            return dic.values()[0]
        return dic
                    

    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'members' : [v.to_dic() for v in self.members] }
        return dic
    
    def parse_tokens(self, token_buf, filepath=None):
        self._filepath = filepath
        brace = token_buf.pop()
        if not brace == '{':
            if self._verbose: sys.stdout.write('# Error. No brace "{".\n')
            raise exception.InvalidIDLSyntaxError()
        
        block_tokens = []        
        while True:

            token = token_buf.pop()
            if token == None:
                if self._verbose: sys.stdout.write('# Error. No brace "}".\n')
                raise exception.InvalidIDLSyntaxError()
            
            elif token == 'union':
                name_ = token_buf.pop()
                m = IDLMember(self)
                u = union.IDLUnion(name_, self)
                u.parse_tokens(token_buf, filepath=filepath)
                m.type = u
                self._members.append(m)
                continue
            
            elif token == '}':
                token = token_buf.pop()
                if not token == ';':
                    if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                    raise exception.InvalidIDLSyntaxError()
                break
            
            if token == ';':
                self._parse_block(block_tokens)
                block_tokens = []
                continue
            block_tokens.append(token)

        self._post_process()
        
        
            
    def _parse_block(self, blocks):
        v = IDLMember(self)
        v.parse_blocks(blocks, self.filepath)
        self._members.append(v)
    
    def _post_process(self):
        self.forEachMember(lambda m : m.post_process())

    @property
    def members(self):
        return self._members

    def member_by_name(self, name):
        for m in self._members:
            if m.name == name:
                return m
        return None
    
    def forEachMember(self, func):
        for m in self._members:
            func(m)
