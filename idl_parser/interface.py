import sys
from . import node, type, exception
from . import struct, union, typedef, enum, const
from . import type as idl_type
from symbol import argument


sep = '::'

class IDLArgument(node.IDLNode):
    def __init__(self, parent):
        super(IDLArgument, self).__init__('IDLArgument', '', parent)
        self._verbose = True
        self._dir = 'in'
        self._type = None

    def parse_blocks(self, blocks, filepath=None):
        self._filepath= filepath
        directions = ['in', 'out']
        nodirections = ['inout']
        self._dir = 'in'
        if blocks[0] in nodirections:
            raise exception.InvalidIDLSyntaxError("-- ERROR invalid direction for %s parameter" %(blocks[0]))
        if blocks[0] in directions:
            self._dir = blocks[0]
            blocks.pop(0)
            pass
        argument_name, argument_type, argument_annotation = self._name_and_type(blocks)
        self._name = argument_name
        self._type = idl_type.IDLType(argument_type, self)

    def to_simple_dic(self):
        dic = '%s %s %s' % (self.direction, self.type, self.name)
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'classname' : self.classname,
                'type' : str(self.type),
                'direction' : self.direction,
                'filepath' : self.filepath }
        return dic

    @property
    def direction(self):
        return self._dir

    @property
    def type(self):
        return self._type

    def post_process(self):
        #self._type = self.refine_typename(self.type)
        pass

        
class IDLMethod(node.IDLNode):
    def __init__(self, parent):
        super(IDLMethod, self).__init__('IDLValue', '', parent)
        self._verbose = True
        self._annotations = ''
        self._returns = None
        self._arguments = []
        

    def parse_blocks(self, blocks, filepath=None):
        self._filepath=filepath
        self._oneway = False
        self._constructor = False
        self._destructor = False

        if blocks[0] == 'oneway':
            self._oneway = True
            blocks.pop(0)
        elif blocks[0] == 'constructor':
            self._constructor = True
            blocks.pop(0)
        elif blocks[0] == 'destructor':
            self._destructor = True
            blocks.pop(0)
        
        index = 4
        
        if self._constructor or self._destructor:
            self._name = blocks[0]
            index = 3
        else:
            self._returns = idl_type.IDLType(blocks[0], self)
            self._name = blocks[1]
        self._arguments = []

        if not blocks[index-2].startswith('@'):
            print(' -- Invalid Method Annotation (%s) expected @',blocks[index-2])
            raise exception.InvalidIDLSyntaxError()
            
        if not blocks[index-1] == '(':
            print(' -- Invalid Method Token (%s) expected (',blocks[index-1])
            raise exception.InvalidIDLSyntaxError()
        
        self._annotations = blocks[index-2]
        argument_blocks = []
        while True:
            if index == len(blocks):
                break
            token = blocks[index]
            if token == ',' or token == ')':
                if len(argument_blocks) == 0:
                    break

                a = IDLArgument(self)
                self._arguments.append(a)
                a.parse_blocks(argument_blocks, self.filepath)

                argument_blocks = []
            else:
                argument_blocks.append(token)
            index = index + 1

    def to_simple_dic(self):
        return {self.name : {
                'returns' : str(self.returns),
                'params' : [a.to_simple_dic() for a in self.arguments]}}

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath,
                'classname' : self.classname,
                'returns' : str(self._returns),
                'arguments' : [a.to_dic() for a in self.arguments]}
        return dic

    @property
    def returns(self):
        return self._returns

    @property
    def annotations(self):
        return self._annotations

    @property
    def arguments(self):
        return self._arguments

    def argument_by_name(self, name):
        for a in self.arguments:
            if a.name == name:
                return a
        return None


    def forEachArgument(self, func):
        for a in self.arguments:
            func(a)

    def post_process(self):
        #self._returns = self.refine_typename(self.returns)
        #self.forEachArgument(lambda a : a.post_process())
        pass




class IDLInterface(node.IDLNode):
    
    def __init__(self, name, parent):
        super(IDLInterface, self).__init__('IDLInterface', name, parent)
        self._verbose = True
        self._publicsection = []
        self._protectedsection = []
        self._privatesection = []
        
    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        dic = {'interface' : [a.to_simple_dic(quiet) for a in self.publicsection] +
                             [b.to_simple_dic(quiet) for b in self.protectedsection] +
                             [c.to_simple_dic(quiet) for c in self.privatesection]}
        return dic
        

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath, 
                'classname' : self.classname,
                'public' : [a.to_dic() for a in self.publicsection],
                'protected' : [b.to_dic() for b in self.protectedsection],
                'private' : [c.to_dic() for c in self.privatesection]}
        return dic
    
    
    def parse_tokens(self, token_buf, filepath=None):
        self._filepath=filepath
        brace = token_buf.pop()
        if not brace == '{':
            if self._verbose: sys.stdout.write('# Error. No brace "{".\n')
            raise exception.InvalidIDLSyntaxError()
        
        while True:

            token = token_buf.pop()
            if token == None:
                if self._verbose: sys.stdout.write('# Error. No brace "}".\n')
                raise exception.InvalidIDLSyntaxError()
                
            elif token == 'public:':
                name_ = 'public'
                a = self.public_by_name(name_)
                if a == None:
                    a = IDLPublicInterfaceSection(name_, self)
                    self._publicsection.append(a)
                a.parse_tokens(token_buf, filepath=filepath)
                
            
            elif token == 'protected:':
                name_ = 'protected'
                b = self.protected_by_name(name_)
                if b == None:
                    b = IDLProtectedInterfaceSection(name_, self)
                    self._protectedsection.append(b)
                b.parse_tokens(token_buf, filepath=filepath)

                
            elif token == 'private:':
                name_ = 'private'
                c = self.private_by_name(name_)
                if c == None:
                    c = IDLPrivateInterfaceSection(name_, self)
                    self._privatesection.append(c)
                c.parse_tokens(token_buf, filepath=filepath)
            
               
            
    
            elif token == '}':
                token = token_buf.pop()
                if not token == ';':
                    if self._verbose: sys.stdout.write('# Error. No semi-colon after "}".\n')
                    raise exception.InvalidIDLSyntaxError()
                break
            
        return True



    
    @property
    def publics(self):
        return self._publicsection

    def public_by_name(self, name):
        for a in self.publics:
            if name == a.name:
                return a
        return None

    def for_each_public(self, func):
        for a in self.publics:
            func(a)

    @property
    def protecteds(self):
        return self._protectedsection

    def protected_by_name(self, name):
        for b in self.protecteds:
            if name == b.name:
                return b
        return None

    def for_each_protected(self, func):
        for b in self.protecteds:
            func(b)
            
    @property
    def privates(self):
        return self._privatesection

    def private_by_name(self, name):
        for c in self.privates:
            if name == c.name:
                return c
        return None

    def for_each_private(self, func):
        for c in self.privates:
            func(c)
    

    

   
            


    def find_types(self, full_typename):
        if type.is_primitive(full_typename):
            return [type.IDLType(full_typename, self)]
        typenode = []

        def parse_node(s, name=str(full_typename)):
            if s.name == name.strip() or s.full_path == name.strip():
                typenode.append(s)

        def parse_module(i):
            i.for_each_public(parse_function)
            i.for_each_protected(parse_function)
            i.for_each_private(parse_function)
            
        def parse_function(m):
            typefull = m.find_types(full_typename)
            if (typefull.__len__() > 0):
                typenode.append(typefull)

        parse_module(self)

        return typenode



############################################################################################################################################
# fsimone: inserite 3 nuove classi per gestire sezioni di metodi IDL con parte pubblica, privata o protetta
############################################################################################################################################



############################
# CLASS FOR PUBLIC SECTION #
############################
class IDLPublicInterfaceSection(node.IDLNode):
    
    def __init__(self, name, parent):
        super(IDLPublicInterfaceSection, self).__init__('IDLPublicInterfaceSection', name, parent)
        self._verbose = True
        self._methods = []
        self._typedefs = []
        self._structs = []
        self._unions = []
        self._enums = []
        self._consts = []
        
    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        if quiet:
            return 'interface %s' % self.name
        dic = { 'interface ' + self.name : [s.to_simple_dic(quiet) for s in self.structs] + 
               [m.to_simple_dic() for m in self.methods] +
               [e.to_simple_dic(quiet) for e in self.enums] + 
               [u.to_simple_dic(quiet) for u in self.unions] + 
               [t.to_simple_dic(quiet) for t in self.typedefs] + 
               [t.to_simple_dic(quiet) for t in self.consts] }
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath, 
                'classname' : self.classname,
                'typedefs' : [t.to_dic() for t in self.typedefs],
                'structs' : [s.to_dic() for s in self.structs],
                'unions' : [u.to_dic() for u in self.structs],
                'enums' : [e.to_dic() for e in self.enums],
                'consts' : [c.to_dic() for c in self.consts],
                'methods' : [m.to_dic() for m in self.methods] }
        return dic
    
    def parse_tokens(self, token_buf, filepath=None):
        self._filepath=filepath
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
                
            elif token == 'typedef':
                blocks = []
                while True:
                    t = token_buf.pop()
                    if t == None:
                        raise exception.InvalidIDLSyntaxError()
                    elif t == ';':
                        break
                    else:
                        blocks.append(t)
                t = typedef.IDLTypedef(self)
                self._typedefs.append(t)
                t.parse_blocks(blocks, filepath=filepath)
                
                continue
                
            elif token == 'struct':
                name_ = token_buf.pop()
                s_ = self.struct_by_name(name_)
                s = struct.IDLStruct(name_, self)
                s.parse_tokens(token_buf, filepath=filepath)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Struct Defined (%s)\n' % name_)
                #    raise exception.InvalidIDLSyntaxError
                else:
                    self._structs.append(s)
                continue

            elif token == 'union':
                name_ = token_buf.pop()
                u_ = self.union_by_name(name_)
                u = union.IDLUnion(name_, self)
                u.parse_tokens(token_buf, filepath=filepath)
                if u_:
                    if self._verbose: sys.stdout.write('# Error. Same Union Defined (%s)\n' % name_)
                #    raise exception.InvalidIDLSyntaxError
                else:
                    self._unions.append(u)
                continue

            elif token == 'enum':
                name_ = token_buf.pop()
                s = enum.IDLEnum(name_, self)
                s.parse_tokens(token_buf, filepath)
                s_ = self.enum_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Enum Defined (%s)\n' % name_)
                #    raise InvalidIDLSyntaxError
                else:
                    self._enums.append(s)

                continue

            elif token == 'const':
                values = []
                while True:
                    t = token_buf.pop()
                    if t == ';':
                        break
                    values.append(t)
                
                if (values.__len__() < 3):
                    raise exception.InvalidIDLSyntaxError("# Error Invalid syntax in constant definition")

                value_ = values[-1]
                name_ = values[-3]
                typename = values[-2]
                for t in values[:-3]:
                    typename = typename + ' ' + t
                typename = typename.strip()
                s = const.IDLConst(name_, typename, value_, self, filepath=filepath)
                s_ = self.const_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Const Defined (%s)\n' % name_)
                else:
                    self._consts.append(s)
                    
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



    def _post_process(self):
        self.forEachMethod(lambda m : m.post_process())

    def _parse_block(self, blocks):
        v = IDLMethod(self)
        v.parse_blocks(blocks, self.filepath)
        self._methods.append(v)

    @property
    def methods(self):
        return self._methods

    def method_by_name(self, name):
        for m in self.methods:
            if name == m.name:
                return m
        return None

    def forEachMethod(self, func):
        for m in self.methods:
            func(m)

    @property
    def structs(self):
        return self._structs

    def struct_by_name(self, name):
        for s in self.structs:
            if s.name == name:
                return s
        return None

    def for_each_struct(self, func, filter=None):
        retval = []
        for m in self.structs:
            if filter:
                if filter(m):
                    retval.append(func(m))
                pass
            else:
                retval.append(func(m))
        return retval
    
    @property
    def unions(self):
        return self._unions

    def union_by_name(self, name):
        for u in self.unions:
            if u.name == name:
                return u
        return None

    def for_each_union(self, func, filter=None):
        retval = []
        for u in self.unions:
            if filter:
                if filter(u):
                    retval.append(func(u))
                pass
            else:
                retval.append(func(u))
        return retval

    @property
    def enums(self):
        return self._enums

    def enum_by_name(self, name):
        for e in self.enums:
            if e.name == name:
                return e
        return None

    def for_each_enum(self, func):
        retval = []
        for m in self.enums:
            retval.append(func(m))
        return retval

    @property
    def consts(self):
        return self._consts

    def const_by_name(self, name):
        for c in self.consts:
            if c.name == name:
                return c
        return None

    def for_each_const(self, func):
        retval = []
        for m in self.consts:
            retval.append(func(m))
        return retval
            

    @property
    def typedefs(self):
        return self._typedefs

    def typedef_by_name(self, name):
        for t in self.typedefs:
            if t.name == name:
                return t
        return None

    def for_each_typedef(self, func):
        retval = []
        for m in self.typedefs:
            retval.append(func(m))

    def find_types(self, full_typename):
        if type.is_primitive(full_typename):
            return [type.IDLType(full_typename, self)]
        typenode = []

        def parse_node(s, name=str(full_typename)):
            if s.name == name.strip() or s.full_path == name.strip():
                typenode.append(s)

        def parse_module(m):
            #m.for_each_module(parse_module)
            m.for_each_struct(parse_node)
            m.for_each_union(parse_node)
            m.for_each_typedef(parse_node)
            m.for_each_enum(parse_node)
            #m.for_each_interface(parse_function)

        parse_module(self)

        return typenode









###############################
# CLASS FOR PROTECTED SECTION #
###############################
class IDLProtectedInterfaceSection(node.IDLNode):
    
    def __init__(self, name, parent):
        super(IDLProtectedInterfaceSection, self).__init__('IDLProtectedInterfaceSection', name, parent)
        self._verbose = True
        self._methods = []
        self._typedefs = []
        self._structs = []
        self._unions = []
        self._enums = []
        self._consts = []
        
        
    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        if quiet:
            return 'interface %s' % self.name
        dic = { 'interface ' + self.name : [s.to_simple_dic(quiet) for s in self.structs] + 
               [m.to_simple_dic() for m in self.methods] +
               [e.to_simple_dic(quiet) for e in self.enums] + 
               [u.to_simple_dic(quiet) for u in self.unions] + 
               [t.to_simple_dic(quiet) for t in self.typedefs] + 
               [t.to_simple_dic(quiet) for t in self.consts] }
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath, 
                'classname' : self.classname,
                'typedefs' : [t.to_dic() for t in self.typedefs],
                'structs' : [s.to_dic() for s in self.structs],
                'unions' : [u.to_dic() for u in self.structs],
                'enums' : [e.to_dic() for e in self.enums],
                'consts' : [c.to_dic() for c in self.consts],
                'methods' : [m.to_dic() for m in self.methods] }
        return dic
    
    def parse_tokens(self, token_buf, filepath=None):
        self._filepath=filepath
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
                
            elif token == 'typedef':
                blocks = []
                while True:
                    t = token_buf.pop()
                    if t == None:
                        raise exception.InvalidIDLSyntaxError()
                    elif t == ';':
                        break
                    else:
                        blocks.append(t)
                t = typedef.IDLTypedef(self)
                self._typedefs.append(t)
                t.parse_blocks(blocks, filepath=filepath)
                
                continue
                
            elif token == 'struct':
                name_ = token_buf.pop()
                s_ = self.struct_by_name(name_)
                s = struct.IDLStruct(name_, self)
                s.parse_tokens(token_buf, filepath=filepath)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Struct Defined (%s)\n' % name_)
                #    raise exception.InvalidIDLSyntaxError
                else:
                    self._structs.append(s)
                continue
            
            elif token == 'union':
                name_ = token_buf.pop()
                u_ = self.union_by_name(name_)
                u = union.IDLUnion(name_, self)
                u.parse_tokens(token_buf, filepath=filepath)
                if u_:
                    if self._verbose: sys.stdout.write('# Error. Same Union Defined (%s)\n' % name_)
                #    raise exception.InvalidIDLSyntaxError
                else:
                    self._unions.append(u)
                continue

            elif token == 'enum':
                name_ = token_buf.pop()
                s = enum.IDLEnum(name_, self)
                s.parse_tokens(token_buf, filepath)
                s_ = self.enum_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Enum Defined (%s)\n' % name_)
                #    raise InvalidIDLSyntaxError
                else:
                    self._enums.append(s)

                continue

            elif token == 'const':
                values = []
                while True:
                    t = token_buf.pop()
                    if t == ';':
                        break
                    values.append(t)
                
                if (values.__len__() < 3):
                    raise exception.InvalidIDLSyntaxError("# Error Invalid syntax in constant definition")

                value_ = values[-1]
                name_ = values[-3]
                typename = values[-2]
                for t in values[:-3]:
                    typename = typename + ' ' + t
                typename = typename.strip()
                s = const.IDLConst(name_, typename, value_, self, filepath=filepath)
                s_ = self.const_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Const Defined (%s)\n' % name_)
                else:
                    self._consts.append(s)
                    
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



    def _post_process(self):
        self.forEachMethod(lambda m : m.post_process())

    def _parse_block(self, blocks):
        v = IDLMethod(self)
        v.parse_blocks(blocks, self.filepath)
        self._methods.append(v)

    @property
    def methods(self):
        return self._methods

    def method_by_name(self, name):
        for m in self.methods:
            if name == m.name:
                return m
        return None

    def forEachMethod(self, func):
        for m in self.methods:
            func(m)

    @property
    def structs(self):
        return self._structs

    def struct_by_name(self, name):
        for s in self.structs:
            if s.name == name:
                return s
        return None

    def for_each_struct(self, func, filter=None):
        retval = []
        for m in self.structs:
            if filter:
                if filter(m):
                    retval.append(func(m))
                pass
            else:
                retval.append(func(m))
        return retval

    @property
    def unions(self):
        return self._unions

    def union_by_name(self, name):
        for u in self.unionss:
            if u.name == name:
                return u
        return None

    def for_each_union(self, func, filter=None):
        retval = []
        for u in self.unions:
            if filter:
                if filter(u):
                    retval.append(func(u))
                pass
            else:
                retval.append(func(u))
        return retval
    
    @property
    def enums(self):
        return self._enums

    def enum_by_name(self, name):
        for e in self.enums:
            if e.name == name:
                return e
        return None

    def for_each_enum(self, func):
        retval = []
        for m in self.enums:
            retval.append(func(m))
        return retval

    @property
    def consts(self):
        return self._consts

    def const_by_name(self, name):
        for c in self.consts:
            if c.name == name:
                return c
        return None

    def for_each_const(self, func):
        retval = []
        for m in self.consts:
            retval.append(func(m))
        return retval
            

    @property
    def typedefs(self):
        return self._typedefs

    def typedef_by_name(self, name):
        for t in self.typedefs:
            if t.name == name:
                return t
        return None

    def for_each_typedef(self, func):
        retval = []
        for m in self.typedefs:
            retval.append(func(m))

    def find_types(self, full_typename):
        if type.is_primitive(full_typename):
            return [type.IDLType(full_typename, self)]
        typenode = []

        def parse_node(s, name=str(full_typename)):
            if s.name == name.strip() or s.full_path == name.strip():
                typenode.append(s)

        def parse_module(m):
            #m.for_each_module(parse_module)
            m.for_each_struct(parse_node)
            m.for_each_typedef(parse_node)
            m.for_each_enum(parse_node)
            #m.for_each_interface(parse_function)

        parse_module(self)

        return typenode

        
        
        
        
        
        

#############################
# CLASS FOR PRIVATE SECTION #
#############################
class IDLPrivateInterfaceSection(node.IDLNode):
    
    def __init__(self, name, parent):
        super(IDLPrivateInterfaceSection, self).__init__('IDLPrivateInterfaceSection', name, parent)
        self._verbose = True
        self._methods = []
        self._typedefs = []
        self._structs = []
        self._unions = []
        self._enums = []
        self._consts = []


        
    @property
    def full_path(self):
        return self.parent.full_path + sep + self.name

    def to_simple_dic(self, quiet=False, full_path=False, recursive=False, member_only=False):
        if quiet:
            return 'interface %s' % self.name
        dic = { 'interface ' + self.name : [s.to_simple_dic(quiet) for s in self.structs] + 
               [m.to_simple_dic() for m in self.methods] +
               [e.to_simple_dic(quiet) for e in self.enums] + 
               [u.to_simple_dic(quiet) for u in self.unions] + 
               [t.to_simple_dic(quiet) for t in self.typedefs] + 
               [t.to_simple_dic(quiet) for t in self.consts] }
        return dic

    def to_dic(self):
        dic = { 'name' : self.name,
                'filepath' : self.filepath, 
                'classname' : self.classname,
                'typedefs' : [t.to_dic() for t in self.typedefs],
                'structs' : [s.to_dic() for s in self.structs],
                'unions' : [u.to_dic() for u in self.structs],
                'enums' : [e.to_dic() for e in self.enums],
                'consts' : [c.to_dic() for c in self.consts],
                'methods' : [m.to_dic() for m in self.methods] }
        return dic
    
    def parse_tokens(self, token_buf, filepath=None):
        self._filepath=filepath
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
                
            elif token == 'typedef':
                blocks = []
                while True:
                    t = token_buf.pop()
                    if t == None:
                        raise exception.InvalidIDLSyntaxError()
                    elif t == ';':
                        break
                    else:
                        blocks.append(t)
                t = typedef.IDLTypedef(self)
                self._typedefs.append(t)
                t.parse_blocks(blocks, filepath=filepath)
                
                continue
                
            elif token == 'struct':
                name_ = token_buf.pop()
                s_ = self.struct_by_name(name_)
                s = struct.IDLStruct(name_, self)
                s.parse_tokens(token_buf, filepath=filepath)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Struct Defined (%s)\n' % name_)
                #    raise exception.InvalidIDLSyntaxError
                else:
                    self._structs.append(s)
                continue
            
            elif token == 'union':
                name_ = token_buf.pop()
                u_ = self.union_by_name(name_)
                u = union.IDLUnion(name_, self)
                u.parse_tokens(token_buf, filepath=filepath)
                if u_:
                    if self._verbose: sys.stdout.write('# Error. Same Union Defined (%s)\n' % name_)
                #    raise exception.InvalidIDLSyntaxError
                else:
                    self._unions.append(u)
                continue

            elif token == 'enum':
                name_ = token_buf.pop()
                s = enum.IDLEnum(name_, self)
                s.parse_tokens(token_buf, filepath)
                s_ = self.enum_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Enum Defined (%s)\n' % name_)
                #    raise InvalidIDLSyntaxError
                else:
                    self._enums.append(s)

                continue

            elif token == 'const':
                values = []
                while True:
                    t = token_buf.pop()
                    if t == ';':
                        break
                    values.append(t)
                
                if (values.__len__() < 3):
                    raise exception.InvalidIDLSyntaxError("# Error Invalid syntax in constant definition")

                value_ = values[-1]
                name_ = values[-3]
                typename = values[-2]
                for t in values[:-3]:
                    typename = typename + ' ' + t
                typename = typename.strip()
                s = const.IDLConst(name_, typename, value_, self, filepath=filepath)
                s_ = self.const_by_name(name_)
                if s_:
                    if self._verbose: sys.stdout.write('# Error. Same Const Defined (%s)\n' % name_)
                else:
                    self._consts.append(s)
                    
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



    def _post_process(self):
        self.forEachMethod(lambda m : m.post_process())

    def _parse_block(self, blocks):
        v = IDLMethod(self)
        v.parse_blocks(blocks, self.filepath)
        self._methods.append(v)

    @property
    def methods(self):
        return self._methods

    def method_by_name(self, name):
        for m in self.methods:
            if name == m.name:
                return m
        return None

    def forEachMethod(self, func):
        for m in self.methods:
            func(m)

    @property
    def structs(self):
        return self._structs

    def struct_by_name(self, name):
        for s in self.structs:
            if s.name == name:
                return s
        return None

    def for_each_struct(self, func, filter=None):
        retval = []
        for m in self.structs:
            if filter:
                if filter(m):
                    retval.append(func(m))
                pass
            else:
                retval.append(func(m))
        return retval
    
    @property
    def unions(self):
        return self._unions

    def union_by_name(self, name):
        for u in self.unionss:
            if u.name == name:
                return u
        return None

    def for_each_union(self, func, filter=None):
        retval = []
        for u in self.unions:
            if filter:
                if filter(u):
                    retval.append(func(u))
                pass
            else:
                retval.append(func(u))
        return retval

    @property
    def enums(self):
        return self._enums

    def enum_by_name(self, name):
        for e in self.enums:
            if e.name == name:
                return e
        return None

    def for_each_enum(self, func):
        retval = []
        for m in self.enums:
            retval.append(func(m))
        return retval

    @property
    def consts(self):
        return self._consts

    def const_by_name(self, name):
        for c in self.consts:
            if c.name == name:
                return c
        return None

    def for_each_const(self, func):
        retval = []
        for m in self.consts:
            retval.append(func(m))
        return retval
            

    @property
    def typedefs(self):
        return self._typedefs

    def typedef_by_name(self, name):
        for t in self.typedefs:
            if t.name == name:
                return t
        return None

    def for_each_typedef(self, func):
        retval = []
        for m in self.typedefs:
            retval.append(func(m))

    def find_types(self, full_typename):
        if type.is_primitive(full_typename):
            return [type.IDLType(full_typename, self)]
        typenode = []

        def parse_node(s, name=str(full_typename)):
            if s.name == name.strip() or s.full_path == name.strip():
                typenode.append(s)

        def parse_interface(m):
            #m.for_each_module(parse_module)
            m.for_each_struct(parse_node)
            m.for_each_typedef(parse_node)
            m.for_each_enum(parse_node)
            #m.for_each_interface(parse_function)

        parse_interface(self)

        return typenode


       
