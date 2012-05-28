from uliweb.core.template import Node
from uliweb import functions

class PermissionNode(Node):
    block = 1
    def __init__(self, name='', content=None):
        self.nodes = []
        self.name = name.strip()
        self.content = content
        self.func = functions.has_permission
        
    def add(self, node):
        self.nodes.append(node)

    def __repr__(self):
        s = ['{{permission %s}}' % self.name]
        for x in self.nodes:
            s.append(repr(x))
        s.append('{{end}}')
        return ''.join(s)
    
    def __str__(self):
        return self.render()
    
    def render(self):
        """
        Top: if output the toppest block node
        """
        from uliweb import request, functions
#        if top and self.name in self.content.root.block_vars and self is not self.content.root.block_vars[self.name][-1]:
#            return self.content.root.block_vars[self.name][-1].render(False)
#        
        #check the permission
        s = []
        if self.func(request.user, self.name):
            for x in self.nodes:
                s.append(str(x))
        return ''.join(s)
    
class RoleNode(PermissionNode):
    def __init__(self, name='', content=None):
        super(RoleNode, self).__init__(name, content)
        self.func = functions.has_role
    