# Prints all targets and keywords used in Pants BUILD dsl.
# $ cd commons/src/python/twitter/pants
# $ cat __init__.py targets/*.py|python parse_pants_targets_and_keywords.py -t|sort|uniq|awk '{print "  \\ "$1}'

import sys
import ast

from optparse import OptionParser

class ClassHierarchyResolver(ast.NodeVisitor):
  def __init__(self, node):
    self.class_hierarchy = dict()
    self.visit(node)

  def visit_ClassDef(self, node):
    base = node.bases[0]
    self.class_hierarchy[node.name] = base.id

  def resolve(self, name):
    if name in self.class_hierarchy:
      base = self.class_hierarchy[name]
      return self.resolve(base)
    else:
      return name

class AssignResolver(ast.NodeVisitor):
  def __init__(self, node):
    self.assigns = dict()
    self.visit(node)

  def visit_Assign(self, node):
    if hasattr(node.value, "id"):
      for t in node.targets:
        if hasattr(t, "id"):
          self.assigns[t.id] = node.value.id

  def resolve(self, name):
    if name in self.assigns:
      assign = self.assigns[name]
      return self.resolve(assign)
    else:
      return name

class TargetClassVisitor(ast.NodeVisitor):
  def __init__(self, class_hierarchy_resolver):
    self.targets = set()
    self.class_hierarchy_resolver = class_hierarchy_resolver

  def visit_ClassDef(self, node):
    base = self.class_hierarchy_resolver.resolve(node.name)
    if base == "Target" or base == "object":
      self.targets.add(node)

class InitFunctionVisitor(ast.NodeVisitor):
  def __init__(self):
    self.keywords = set()

  def visit_FunctionDef(self, node):
    if node.name == "__init__":
      for a in node.args.args:
        if a.id != "self":
          self.keywords.add(a.id)

class PantsParser:
  def parse_args(self):
    parser = OptionParser()
    parser.add_option("-t", "--targets", dest="print_targets", action="store_true",
                      help="print all pants targets")
    parser.add_option("-k", "--keywords", dest="print_keywords", action="store_true",
                      help="print all pants keywords")
    options, args = parser.parse_args()
    return options

  def run(self):
    options = self.parse_args()
    source = sys.stdin.read()
    root_node = ast.parse(source)

    class_hierarchy_resolver = ClassHierarchyResolver(root_node)
    assign_resolver = AssignResolver(root_node)

    target_class_visitor = TargetClassVisitor(class_hierarchy_resolver)
    target_class_visitor.visit(root_node)
    target_class_nodes = target_class_visitor.targets

    if options.print_targets:
      target_class_names = set([node.name for node in target_class_nodes])

      # Print all pants Target class names
      for name in target_class_names:
        print name

      # Print all alias names to Target classes
      for assign in assign_resolver.assigns:
        name = assign_resolver.resolve(assign)
        if name in target_class_names:
          print assign

    if options.print_keywords:
      # Print all named arguments for Target classes __init__.
      for node in target_class_nodes:
        init_function_visitor = InitFunctionVisitor()
        init_function_visitor.visit(node)
        for keyword in init_function_visitor.keywords:
          print keyword

def main():
  PantsParser().run()

main()
