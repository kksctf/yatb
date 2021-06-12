import markdown
from typing import Dict, Optional


class ClassAdderTreeprocessor(markdown.treeprocessors.Treeprocessor):
    def run(self, root):
        self.set_css_class(root)
        return root

    def set_config(self, ext):
        self.ext = ext

    def set_css_class(self, element):
        for child in element:
            # if child.tag == "p":
            #    child.set("class", self.ext.getConfig("css_class"))  # set the class attribute
            cl = self.ext.get_class_for_tag(child.tag)
            if cl:
                child.set("class", cl)
            self.set_css_class(child)  # run recursively on children


class ClassAdderExtension(markdown.Extension):
    def __init__(self, *args, **kwargs):
        self.config = {
            "replace": [
                {},
                "replace - Default: {}",
            ],
        }
        # Override defaults with user settings
        for key, value in kwargs.items():
            self.setConfig(key, value)

    def get_class_for_tag(self, tag) -> Optional[str]:
        if tag in self.getConfig("replace"):
            return self.getConfig("replace")[tag]
        return None

    def extendMarkdown(self, md, md_globals):
        treeprocessor = ClassAdderTreeprocessor(md)
        treeprocessor.set_config(self)
        md.treeprocessors.register(treeprocessor, "class-ext", 0)


class AttributeTreeprocessor(markdown.treeprocessors.Treeprocessor):
    def run(self, root):
        self.set_attrs(root)
        return root

    def set_config(self, ext):
        self.ext = ext

    def set_attrs(self, element):
        for child in element:
            attrs = self.ext.get_attrs_for_tag(child.tag)
            if attrs:
                for attr_name in attrs:
                    child.set(attr_name, attrs[attr_name])
            self.set_attrs(child)  # run recursively on children


class AttributeExtension(markdown.Extension):
    def __init__(self, *args, **kwargs):
        self.config = {"attrs": [{}, "attrs - Default: {}"]}
        # Override defaults with user settings
        for key, value in kwargs.items():
            self.setConfig(key, value)

    def get_attrs_for_tag(self, tag) -> Optional[str]:
        if tag in self.getConfig("attrs"):
            return self.getConfig("attrs")[tag]
        return None

    def extendMarkdown(self, md, md_globals):
        treeprocessor = AttributeTreeprocessor(md)
        treeprocessor.set_config(self)
        md.treeprocessors.register(treeprocessor, "attrib-ext", 0)
        # ['css'] =


def markdownCSS(txt, config, attrs_config={}):
    ext = ClassAdderExtension(replace=config)
    ext_attrs = AttributeExtension(attrs=attrs_config)
    md = markdown.Markdown(extensions=[ext, ext_attrs], safe_mode="escape")
    html = md.convert(txt)
    return html
