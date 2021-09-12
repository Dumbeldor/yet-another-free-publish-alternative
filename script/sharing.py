import re
import sys
import os
from dotenv import dotenv_values
from pathlib import Path
from pathlib import PurePath
import shutil
from datetime import datetime
import frontmatter
import yaml

BASEDIR = os.path.abspath(os.path.dirname(__file__))
if 'script' in BASEDIR:
    BASEDIR = PurePath(BASEDIR).parents[0]
env = dotenv_values(Path(f"{BASEDIR}/.env"))
path = Path(f"{BASEDIR}/.git")  # GIT SHARED
vault = Path(env["vault"])
post = Path(f"{BASEDIR}/_notes")
blog = env["blog"]
img = Path(f"{BASEDIR}/assets/img/")

# Seems to have problem with dotenv with pyto on IOS 15
try:
    vault = Path(env["vault"])
    blog = env["blog"]
except KeyError:
    with open(Path(f"{BASEDIR}/.env")) as f:
        vault = Path(''.join(f.readlines(1)).replace("vault=", ""))
        blog = ''.join(f.readlines(2)).replace("blog=", '')

def retro(filepath):
    # It permit to compare the file in file diff with len(file)
    # Remove newline, comments and frontmatter
    notes = []
    metadata = frontmatter.load(filepath)
    file = metadata.content.split("\n")
    for n in file:
        if n != "\\":
            n = n.strip()
            notes.append(n)
    notes = [i for i in notes if i != ""]
    notes = [i for i in notes if "%%" not in i]
    return notes

def remove_date_title(meta):
    meta.metadata.pop('date', None)
    meta.metadata.pop('title', None)
    return meta.metadata

def diff_file(file):
    file_name = os.path.basename(file)
    if check_file(file_name) == "EXIST":
        vault_path = file
        notes_path = Path(f"{BASEDIR}/_notes/{file_name}")
        vault = retro(vault_path)
        notes = retro(notes_path)
        # Compare front matter because edit frontmatter is important too
        meta_notes = frontmatter.load(notes_path)
        meta_vault = frontmatter.load(vault_path)
        metadata_notes=remove_date_title(meta_notes)
        metadata_vault = remove_date_title(meta_vault)
        if len(vault) == len(notes) or sorted(metadata_notes.keys()) != sorted(metadata_vault.keys()):
            return False
        else:
            return True

def admonition_trad_type(line):
    #Admonition Obsidian : blockquote + ad-
    # Admonition md template : ```ad-type <content> ```
    #build dictionnary for different types
    admonition = {'note':'note', 'seealso': 'note', 'abstract' : 'abstract', 'summary':'abstract', 'tldr': 'abstract', 'info':'todo', 'todo':'todo', 'tip':'tip', 'hint':'tip', 'important':'tip', 'success':'done', 'check':'done', 'done':'done', 'question':'question', 'help': 'question', 'faq':'question',  'warning':'warning', 'caution':'warning', 'attention':'warning', 'failure':'failure', 'fail':'failure', 'missing':'failure', 'danger':'danger', 'error':'danger', 'bug':'bug', 'example':'example', 'exemple':'example', 'quote':'quote', 'cite':'quote'}
    admonition_type = re.search('```ad-(.*)', line)
    ad_type = line
    content_type=""
    if admonition_type:
        admonition_type=admonition_type.group(1)
        if admonition_type.lower() in admonition.keys(): #found type
            content_type = admonition[admonition_type]
            ad_type= '{: .'+ content_type +'}  \n'
        else:
            ad_type = '{: .note}  \n'
            content_type= "custom" + admonition_type  #if admonition "personnal" type, use note by default
    return ad_type, content_type

def admonition_trad_title(line, content_type):
    #Admonition title always are : 'title:(.*)' so...
    ad_title= re.search('title:(.*)', line)
    title = line
    if ad_title:
        # get content title
        title_group=ad_title.group(1)
        if "custom" in content_type:
            content_type = "note"
        if ad_title == "":
            title = "> " + line  # admonition inline
        else:
            title_md = '> **'+title_group.strip()+'**{: .ad-title-' + content_type + '}'
            title = re.sub('title:(.*)', title_md, line)
    else:
        if 'collapse:' in line :
            title = ""
        elif 'icon:' in line:
            title = ""
        elif 'color:' in line:
            title = ""
        elif len(line) == 1:
            title = ""
        else:
            title = "> " + line #admonition inline
    return title


def admonition_trad(file_data):
    code_index = 0
    code_dict={}
    start = 0
    end = 0
    start_list = []
    end_list = []
    for i in range (0, len(file_data)):
        if re.search('```ad-(.*)', file_data[i]):
            start = i
            start_list.append(start)
        elif re.match('```', file_data[i]) :
            end = i
            end_list.append(end)
    for i,j in zip(start_list, end_list):
        code = {code_index:(i, j)}
        code_index = code_index+1
        code_dict.update(code)
    for ad, ln in code_dict.items():
        ad_start = ln[0]
        ad_end = ln[1]
        file_data[ad_start], ad_type=admonition_trad_type(file_data[ad_start])
        ad_type=ad_type
        code_block = [x for x in range(ad_start+1, ad_end)]
        for fl in code_block:
            if "custom" in ad_type :
                custom_type = ad_type.replace("custom", "")
                custom_type = custom_type.replace('-', ' ')
                ad_title = re.search('title:(.*)', file_data[fl])
                if not ad_title:
                    file_data[ad_start] =  "{: .note}  \n> **" + custom_type.strip().title() + "**{: .ad-title-note}  \n"
                else:
                    ad_title = ad_title.group(1)
                    file_data[ad_start] = "{: .note} \n > **[" + custom_type.strip().title() + "] " + ad_title.title()  +"**{: .ad-title-note}  \n"
            file_data[fl] = admonition_trad_title(file_data[fl], ad_type)
        file_data[ad_end] = ''
    return file_data

def delete_file(filepath):
    for file in os.listdir(post):
        filepath = os.path.basename(filepath)
        filecheck = os.path.basename(file)
        if filecheck == filepath:
            os.remove(Path(f"{BASEDIR}/_notes/{file}"))
            return True
    return False


def get_image(image):
    image = os.path.basename(image)
    for sub, dirs, files in os.walk(vault):
        for file in files:
            filepath = sub + os.sep + file
            if image in file:
                return filepath


def move_img(line):
    img_flags = re.search("[\|\+\-](.*)[]{1,2})]", line)
    if img_flags:
        img_flags = img_flags.group(0)
        img_flags = img_flags.replace("|", "")
        img_flags = img_flags.replace("]", "")
        img_flags = img_flags.replace(")", "")
        img_flags.replace("(", "")
    else:
        img_flags = ""
    final_text = re.search("(\[{2}|\().*\.(png|jpg|jpeg|gif)", line)
    final_text = final_text.group(0)
    final_text = final_text.replace("(", "")
    final_text = final_text.replace("%20", " ")
    final_text = final_text.replace("[", "")
    final_text = final_text.replace("]", "")
    final_text = final_text.replace(")", "")
    image_path = get_image(final_text)
    final_text = os.path.basename(final_text)
    img_flags = img_flags.replace(final_text, "")
    img_flags = img_flags.replace("(", "")
    if image_path:
        shutil.copyfile(image_path, f"{img}/{final_text}")
        final_text = f"../assets/img/{final_text}"
        final_text = f"![{img_flags}]({final_text})"
        final_text = re.sub('!?(\[{1,2}|\().*\.(png|jpg|jpeg|gif)(.*)(\]{2}|\))', final_text, line)
    else:
        final_text = line
    return final_text


def relative_path(data):
    data = data.rstrip() + ".md"
    data = os.path.basename(data)
    for sub, dirs, files in os.walk(vault):
        for file in files:
            filepath = sub + os.sep + file
            if data == file:
                return filepath


def check_file(filepath):
    for file in os.listdir(post):
        if filepath == file:
            return "EXIST"
    return "NE"


def dest(filepath):
    file_name = os.path.basename(filepath)
    dest = Path(f"{BASEDIR}/_notes/{file_name}")
    return str(dest)


def convert_no_embed(line):
    final_text = line
    if re.match("\!\[{2}", line) and not re.match("(.*)\.(png|jpg|jpeg|gif)", line):
        final_text = line.replace("!", "")  # remove "!"
        final_text = re.sub('#\^(.*)', "]]", final_text) #Link to block doesn't work
    return final_text



def convert_to_wikilink(line):
    final_text = line
    if not re.search('\[\[', final_text) and re.search(
            '\[(.*)]\((.*)\)', final_text
            ) and not re.search('https', final_text):  # link : [name](file#title) (and not convert external_link)
        title = re.search('\[(.*)]', final_text)
        title = title.group(1)
        link = re.search('\((.*)\)', final_text)
        link = link.group(1)
        link = link.replace('%20', " ")
        wiki = f"[[{link.replace('.md', '')}|{title}]] "
        final_text= re.sub('\[(.*)]\((.*)\)', wiki, final_text)

    return final_text

def transluction_note(line):
    # If file (not image) start with "![[" : transluction with rmn-transclude (exclude
    # image from that)
    # Note : Doesn't support partial transluction for the moment ; remove title
    final_text = line
    if re.search("\!\[", line) and not re.search("(png|jpg|jpeg|gif)", line):
        final_text = line.replace("!", "")  # remove "!"
        final_text = re.sub("#(.*)", "]]", final_text)
        final_text = re.sub("]]", "::rmn-transclude]]", final_text)
        # Add transluction_note
    return final_text

def frontmatter_check(filename):
    metadata = open(Path(f"{BASEDIR}/_notes/{filename}"), "r", encoding="utf-8")
    meta = frontmatter.load(metadata)
    update = frontmatter.dumps(meta)
    metadata.close()
    final = open(Path(f"{BASEDIR}/_notes/{filename}"), "w", encoding="utf-8")
    if not "date" in meta.keys():
        now = datetime.now().strftime("%d-%m-%Y")
        meta["date"] = now
        update = frontmatter.dumps(meta)
        meta = frontmatter.loads(update)
    if not "title" in meta.keys():
        meta["title"] = filename.replace(".md", "")
        update = frontmatter.dumps(meta)
    final.write(update)
    final.close()
    return


def clipboard(filepath):
    filename = os.path.basename(filepath)
    filename = filename.replace(".md", "")
    filename=filename.replace(" ","-")
    clip=f"{blog}{filename}"
    if sys.platform == "ios":
        try:
            import pasteboard  # work with pyto

            pasteboard.set_string(clip)
        except ImportError:
            try:
                import clipboard  # work with pytonista

                clipboard.set(clip)
            except ImportError:
                print(
                    "Please, report issue with your OS and configuration to check if it possible to use another clipboard manager"
                )
    else:
        try:
            # trying to use Pyperclip
            import pyperclip

            pyperclip.copy(clip)
        except ImportError:
            print(
                "Please, report issue with your OS and configuration to check if it possible to use another clipboard manager"
            )


def file_convert(file):
    file_name = os.path.basename(file)
    if not "_notes" in file:
        if not os.path.exists(Path(f"{BASEDIR}/_notes/{file_name}")):
            data = open(file, "r", encoding="utf-8")
            meta = frontmatter.load(file)
            final = open(Path(f"{BASEDIR}/_notes/{file_name}"), "w", encoding="utf-8")
            lines = data.readlines()
            data.close()
            if 'share' not in meta.keys() or meta["share"] is False:
                return
            for ln in lines:
                final_text = ln.replace("\n", "  \n")
                final_text=convert_to_wikilink(final_text)
                final_text = re.sub('\^\w+', '', final_text) #remove block id
                if 'embed' in meta.keys() and meta['embed'] == False:
                    final_text = convert_to_wikilink(final_text)
                    final_text = convert_no_embed(final_text)
                else:
                    final_text = transluction_note(final_text)
                if re.search("\%\%(.*)\%\%", final_text):
                    final_text = "  \n"
                elif re.search("==(.*)==", final_text):
                    final_text = re.sub("==", "[[", final_text, 1)
                    final_text = re.sub("( ?)==", "::highlight]] ", final_text, 2)
                elif re.search(
                    "(\[{2}|\().*\.(png|jpg|jpeg|gif)", final_text
                ):  # CONVERT IMAGE
                    final_text = move_img(final_text)
                elif (
                    "\\" in final_text.strip()
                ):  # New line when using "\" in obsidian file
                    final_text = "  \n"
                elif re.search("(\[{2}|\[).*", final_text):
                    # Escape pipe for link name
                    final_text = final_text.replace("|", "\|")
                    # Remove block ID (because it doesn't work)
                    final_text = re.sub('#\^(.*)]]', "]]", final_text)
                    final_text = final_text + "  \n"
                final.write(final_text)
            final.close()
            frontmatter_check(file_name)
            return True
        else:
            meta = frontmatter.load(file)
            if not meta["share"] or meta["share"] == False:
                delete_file(file)
            return False
    else:
        return False


def search_share(option=0):
    filespush = []
    for sub, dirs, files in os.walk(vault):
        for file in files:
            filepath = sub + os.sep + file
            if filepath.endswith(".md") and "excalidraw" not in filepath:
                try:
                    yaml_front = frontmatter.load(filepath)
                    if "share" in yaml_front and yaml_front["share"] is True:
                        if option == 1:
                            if diff_file(filepath):
                                delete_file(filepath)
                        if option == 2:
                            delete_file(filepath)
                        check = file_convert(filepath)
                        destination = dest(filepath)
                        if check:
                            filespush.append(destination)
                except (yaml.scanner.ScannerError, yaml.constructor.ConstructorError) as e :
                    pass

    return filespush


def convert_to_github():
    """
    Create file in _notes, move image in assets, convert to relative path, add share support, and push to git
    ----
    Usage
    -----
        python3 sharing (filepath) (options)
        Optional option:
            - --F : Don't delete file if already exist (prevent update)
            - --f : Force update (delete all file and reform)
            - help : print help message
            - filepath: convert just one file
            - --G : no commit and no push to github.
    """
    if len(sys.argv) >= 2:
        if sys.argv[1] == "help":
            print(help(convert_to_github))
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting convert")
            ori = sys.argv[1]
            delopt = ""
            ng = ""
            if "--F" in sys.argv:
                delopt = "--F"
            elif "--f" in sys.argv:
                delopt = "--f"
            if "--G" in sys.argv:
                ng = "--G"
            if os.path.exists(ori):
                if delopt != "--F":
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Convert {ori} with update"
                    )
                    delete_file(ori)
                else:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Convert {ori} (without update)"
                    )
                check = file_convert(ori)
                if check and ng != "--G":
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Add {ori} to github"
                    )
                    COMMIT = f"{ori} to blog"
                    clipboard(ori)
                    try:
                        import git

                        repo = git.Repo(Path(f"{BASEDIR}/.git"))
                        repo.git.add(".")
                        repo.git.commit("-m", f"{COMMIT}")
                        repo.git.push("origin", "HEAD:refs/for/master")
                        print(
                            f"[{datetime.now().strftime('%H:%M:%S')}] {ori} pushed successfully 🎉"
                        )
                    except ImportError:
                        print(
                            "[{datetime.now().strftime('%H:%M:%S')}] Please, use another way to push your change"
                        )
                elif check and ng == "--G":
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 Successfully converted {ori}"
                    )
                else:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Ori already converted"
                    )

            else:
                if delopt == "--F":
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Convert without update"
                    )
                    new_files = search_share()
                elif delopt == "--f":
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Convert with force update"
                    )
                    new_files = search_share(2)
                else:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Convert with update"
                    )
                    new_files = search_share(1)
                commit = "Add to blog:\n"
                if len(new_files) > 0:
                    for md in new_files:
                        commit = commit + "\n — " + md
                    if ng != "--G":
                        if len(new_files) == 1:
                            md = "".join(new_files)
                            clipboard(md)
                        try:
                            import git

                            repo = git.Repo(Path(f"{BASEDIR}/.git"))
                            repo.git.add(".")
                            repo.git.commit("-m", f"git commit {commit}")
                            origin = repo.remote(name="origin")
                            origin.push()
                            print(
                                f"[{datetime.now().strftime('%H:%M:%S')} {commit}\n pushed successfully 🎉"
                            )
                        except ImportError:
                            print(
                                f"[{datetime.now().strftime('%H:%M:%S')}] Please use another way to push your project"
                            )
                    else:
                        print(
                            f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 Converted "
                            f"{commit.replace('Add to blog', '')}"
                        )
                else:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] File already exists 😶"
                    )

    else:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Starting Convert with update and push "
        )
        new_files = search_share(1)
        commit = "Add to blog :\n"
        if len(new_files) > 0:
            if len(new_files) == 1:
                md = "".join(new_files)
                clipboard(md)
            try:
                import git

                repo = git.Repo(Path(f"{BASEDIR}/.git"))
                for md in new_files:
                    commit = commit + "\n — " + md
                if len(new_files) == 1:
                    md = "".join(new_files)
                    clipboard(md)
                repo.git.add(A=True)
                repo.git.commit(m=commit)
                origin = repo.remote("origin")
                origin.push()
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] {commit}\n pushed successfully 🎉"
                )
            except ImportError:
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Please use working copy"
                )
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] File already exists 😶")


if __name__ == "__main__":
    convert_to_github()