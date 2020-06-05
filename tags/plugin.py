# --------------------------------------------
# Main part of the plugin
#
# David Watkin (c) 2020
# based on mkdocs-tags-plugin by JL Diaz (c) 2019
# MIT License
# --------------------------------------------
from collections  import defaultdict
from pathlib import Path
import yaml
import jinja2
from mkdocs.structure.files import File
from mkdocs.plugins import BasePlugin
from mkdocs.config.config_options import Type


class TagsPlugin(BasePlugin):
    """
    Creates "tags.md" file containing a list of the pages grouped by tags

    It uses the info in the YAML metadata of each page, for the pages which
    provide a "tags" keyword (whose value is a list of strings)
    """

    config_scheme = (
        ('tags_folder', Type(str)),
        ('tags_template', Type(str)),
        ('tags_encoding', Type(str)),
        ('tags_names', Type(list)),
    )

    def __init__(self):
        self.metadata = []
        self.tags_folder = "tags"
        self.tags_template = None
        self.tags_encoding = "cp1252"
        self.tags_names = []

    def on_nav(self, nav, config, files):
        pass

    def on_config(self, config):
        # Re assign the options
        self.tags_encoding = self.config.get("tags_encoding") or "cp1252"
#        self.tags_filename = Path(self.config.get("tags_filename") or self.tags_filename)
        self.tags_folder = Path(self.config.get("tags_folder") or self.tags_folder)
        self.tags_names = self.config.get("tags_names") or []

        # Make sure that the tags folder is absolute, and exists
        if not self.tags_folder.is_absolute():
            self.tags_folder = Path(config["docs_dir"]) / ".." / self.tags_folder
        if not self.tags_folder.exists():
            self.tags_folder.mkdir(parents=True)

        if self.config.get("tags_template"):
            self.tags_template = Path(self.config.get("tags_template"))

    def on_files(self, files, config):
        # Scan the list of files to extract tags from meta
        for f in files:
            if not f.src_path.endswith(".md"):
                continue

            # One-time extract of all the YAML metadata from the file
            self.metadata.append(get_metadata(f.src_path, config["docs_dir"], self.tags_encoding))

        # Create new file with tags
        for tagname in self.tags_names:
            newfilename = self.generate_tags_file(tagname)

            # New file to add to the build
            newfile = File(
                path=str(newfilename),
                src_dir=str(self.tags_folder),
                dest_dir=config["site_dir"],
                use_directory_urls=False
            )
            files.append(newfile)

    def generate_tags_page(self, data, tagname):
        if self.tags_template is None:
            templ_path = Path(__file__).parent  / Path("templates")
            environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(templ_path))
                )
            templ = environment.get_template("tags.md.template")
        else:
            environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(searchpath=str(self.tags_template.parent))
            )
            templ = environment.get_template(str(self.tags_template.name))
        output_text = templ.render(
                tags=sorted(data.items(), key=lambda t: t[0].lower()),
                tagname=tagname,
                title=tagname.capitalize(),
        )
        return output_text

    def generate_tags_file(self, tagname):
        sorted_meta = sorted(self.metadata, key=lambda e: e.get("year", 5000) if e else 0)
        tag_dict = defaultdict(list)
        for e in sorted_meta:
            if not e:
                continue
            if "title" not in e:
                e["title"] = "Untitled"

            tags = e.get(tagname, [])
            if tags is not None:
                for tag in tags:
                    tag_dict[tag].append(e)

        t = self.generate_tags_page(tag_dict, tagname)

        filename = f"{self.tags_folder}/{tagname}.md"
        print("tags file is " + filename)
        with open(str(filename), "w") as f:
            f.write(t)

        return f"{tagname}.md"

# Helper functions

def get_metadata(name, path, encoding):
    # Extract metadata from the yaml at the beginning of the file
    def extract_yaml(f):
        result = []
        inheader = False
        for line in f:
            if line.strip() == "---":
                if inheader:
                    break;
                inheader = True
                continue;
            else:
                if inheader:
                    result.append(line)
        return "".join(result)

    filename = Path(path) / Path(name)
    with filename.open(encoding=encoding) as f:
        metadata = extract_yaml(f)
        if metadata:
            meta = yaml.load(metadata, Loader=yaml.FullLoader)
            meta.update(filename=name)
            return meta
