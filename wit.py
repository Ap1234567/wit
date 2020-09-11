from datetime import datetime
import filecmp
import os
import random
import shutil
import sys

from graphviz import Digraph


class NoWit(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

    def __str__(self):
        return "No '.wit' in an any upper directory."


class FileAlreadySaved(Exception):
    def __init__(self, filename, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.filename = filename

    def __str__(self):
        return f"No changes were made in the data since the last commit. All of the info is saved in '{self.filename}'."

    
class ChangesLeft(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

    def __str__(self):
        return "There are still files in Changes to be comitted or Changes not staged for commit."


def init():
    current_dir = os.getcwd()
    path = os.path.join(current_dir, ".wit")
    if os.path.exists(path):
        print(f"Folder {current_dir} Already has a backup file in it.")
        return 
    os.mkdir(path)
    for i in ("images", "staging_area"):
        os.mkdir(os.path.join(path, i))
    with open(os.path.join(path, "activated.txt"), "w") as act_file:
        act_file.write("master")


def get_wit_path():
    dirs = []
    work_dir = os.getcwd()
    while not os.path.exists(os.path.join(work_dir, ".wit")):
        last_name = os.path.basename(work_dir)
        if work_dir == os.path.dirname(work_dir):
            raise NoWit()
        work_dir = os.path.dirname(work_dir)
        dirs.append(last_name)
    path_parts = {"work_dir": work_dir, "dirs": dirs}
    return path_parts


def move_f(file_to_move_path, go_to_path):
    if os.path.isdir(file_to_move_path):
        shutil.copytree(file_to_move_path, go_to_path)
    elif os.path.isfile(file_to_move_path):
        go_to_path = os.path.dirname(go_to_path)
        if not os.path.exists(go_to_path):
            os.mkdir(go_to_path)
        shutil.copy(file_to_move_path, go_to_path)


def add():
    file_to_move_path = os.path.join(os.getcwd(), sys.argv[2])
    path_parts = get_wit_path()
    work_dir = path_parts["work_dir"]
    dirs = path_parts["dirs"]
    staging_area_path = os.path.join(work_dir, ".wit", "staging_area", *dirs[::-1], sys.argv[2])
    move_f(file_to_move_path, staging_area_path)


def different_folders(staging_area_path, commit_path):
    for data in os.walk(staging_area_path):
        for file in data[2]:
            file_path_in_staging = os.path.join(data[0], file)
            file_path_in_commit = file_path_in_staging.replace(staging_area_path, commit_path)
            if not os.path.exists(file_path_in_commit):
                return True
            cmp1 = filecmp.cmp(file_path_in_staging, file_path_in_commit)
            if not cmp1:
                return True
    return False


def get_branches_dict():
    work_dir = get_wit_path()["work_dir"]
    if not os.path.exists(os.path.join(work_dir, ".wit", "references.txt")):
        return 
    with open(os.path.join(work_dir, ".wit", "references.txt"), "r") as ref:
        list_brn = [y.split("=") for y in ref.read().split("\n")[:-1]]
    dict_brn = {a: b for [a, b] in list_brn}
    return dict_brn


def turn_dict_to_text(branches_dict):
    d = {a: b for [a, b] in branches_dict.items()}
    return "\n".join([a + "=" + b for a, b in d.items()]) + "\n"


def commit():
    work_dir = get_wit_path()["work_dir"]
    if os.path.isfile(os.path.join(work_dir, ".wit", "references.txt")):
        branches_dict = get_branches_dict()
        ref = branches_dict["HEAD"]
        ref_path = os.path.join(work_dir, ".wit", "images", ref)
        staging_area_path = os.path.join(work_dir, ".wit", "staging_area")
        if not different_folders(staging_area_path, ref_path):
            raise FileAlreadySaved(ref)
        parent = ref
    else:
        parent = "None"
    commit_id = "".join(random.choices("1234567890abcdef", k=40))
    commit_id_path = os.path.join(work_dir, ".wit", "images", commit_id)
    os.mkdir(commit_id_path)
    date_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    with open(os.path.join(work_dir, ".wit", "images", commit_id + ".txt"), "w") as commit_txt:
        commit_txt.write(f"parent={parent}\ndate={date_time}\nmessage={sys.argv[2]}")
    staging_area_path = os.path.join(work_dir, ".wit", "staging_area")
    for file in os.listdir(staging_area_path):
        if file != ".wit":
            files_to_move_path = os.path.join(staging_area_path, file)
            move_f(files_to_move_path, os.path.join(commit_id_path, file))
    with open(os.path.join(work_dir, ".wit", "activated.txt"), "r") as active_file:
        active_branch = active_file.read()
    branches_dict = get_branches_dict()
    if branches_dict is not None:
        if branches_dict[active_branch] == branches_dict['HEAD']:
            branches_dict[active_branch] = commit_id
        branches_dict['HEAD'] = commit_id
        with open(os.path.join(work_dir, ".wit", "references.txt"), "w") as ref:
            ref.write(turn_dict_to_text(branches_dict))
    else:
        with open(os.path.join(work_dir, ".wit", "references.txt"), "w") as ref:
            ref.write(f"HEAD={commit_id}\nmaster={commit_id}\n")


def changes_to_be_commited():
    work_dir = get_wit_path()["work_dir"]
    branches_dict = get_branches_dict()
    ref = branches_dict["HEAD"]
    ref_path = os.path.join(work_dir, ".wit", "images", ref)
    staging_area_path = os.path.join(work_dir, ".wit", "staging_area")
    changes_to_be_commited = []
    for data in os.walk(staging_area_path):
        for file in data[2]:
            file_path_in_staging = os.path.join(data[0], file)
            file_path_in_commit = file_path_in_staging.replace(staging_area_path, ref_path)
            if not os.path.exists(file_path_in_commit):
                changes_to_be_commited.append(file)
    return changes_to_be_commited


def changes_not_staged_and_untracked_files():
    work_dir = get_wit_path()["work_dir"]
    staging_area_path = os.path.join(work_dir, ".wit", "staging_area")
    changes_not_staged = []
    untracked_files = []
    for data in os.walk(work_dir):
        if ".wit" not in data[0]:
            for file in data[2]:
                real_file_path = os.path.join(data[0], file)
                file_path_in_staging = real_file_path.replace(work_dir, staging_area_path)
                if os.path.exists(file_path_in_staging):
                    cmp1 = filecmp.cmp(real_file_path, file_path_in_staging)
                    if not cmp1:
                        changes_not_staged.append(file_path_in_staging.replace(staging_area_path, "")[1:])
                else:
                    untracked_files.append(file_path_in_staging.replace(staging_area_path, "")[1:])
    return changes_not_staged, untracked_files


def status():
    changes_not_staged, untracked_files = changes_not_staged_and_untracked_files()
    changes_to_be_commited_in_order = ", ".join(changes_to_be_commited())
    changes_not_staged_in_order = ", ".join(changes_not_staged)
    untracked_files_in_order = ", ".join(untracked_files)
    branches_dict = get_branches_dict()
    ref = branches_dict["HEAD"]
    print(f"Latest backup: {ref}.")
    print(f"Changes to be committed: {changes_to_be_commited_in_order}.")
    print(f"Changes not staged for commit: {changes_not_staged_in_order}.")
    print(f"Untracked Files: {untracked_files_in_order}.")


def remove():
    work_dir = get_wit_path()["work_dir"]
    file_path = os.path.join(work_dir, ".wit", "staging_area", sys.argv[2])
    if not os.path.exists(file_path):
        raise FileNotFoundError()
    os.remove(file_path)
    print(f"{sys.argv[2]} was removed.")


def checkout_commits():
    work_dir = get_wit_path()["work_dir"]
    changes_to_commit = changes_to_be_commited()
    changes_not_staged, untracked_files = changes_not_staged_and_untracked_files()
    if len(changes_to_commit) != 0 or len(changes_not_staged) != 0:
        raise ChangesLeft()
    branches_dict = get_branches_dict()
    current_head = branches_dict["HEAD"]
    if sys.argv[2] == "master":
        commit_id = branches_dict["master"]
    else:
        commit_id = sys.argv[2]
    commit_path = os.path.join(work_dir, ".wit", "images", commit_id)
    if not os.path.exists(commit_path):
        raise FileNotFoundError()
    staging_area_path = os.path.join(work_dir, ".wit", "staging_area")
    full_untracked_files = [os.path.join(work_dir, un_t_file) for un_t_file in untracked_files]
    delete_files(work_dir, full_untracked_files)
    move_all_files(commit_path, work_dir)
    staging_area_path = os.path.join(work_dir, ".wit", "staging_area")
    delete_files(staging_area_path, [])
    move_all_files(commit_path, staging_area_path)
    with open(os.path.join(work_dir, ".wit", "references.txt"), "r") as ref_file:
        current_txt = ref_file.read()
    new_txt = current_txt.replace("HEAD=" + current_head, "HEAD=" + commit_id)
    with open(os.path.join(work_dir, ".wit", "references.txt"), "w") as ref_file:
        ref_file.write(new_txt)


def checkout_branches():
    work_dir = get_wit_path()["work_dir"]
    with open(os.path.join(work_dir, ".wit", "activated.txt"), "w") as act_file:
        act_file.write(f"{sys.argv[2]}")


def checkout():
    work_dir = get_wit_path()["work_dir"]
    branches_dict = get_branches_dict()
    branches_names = list(branches_dict.keys())
    branches_names.remove("HEAD")
    branches_names.remove("master")
    images_path = os.path.join(work_dir, ".wit", "images")
    commits = [commit for commit in os.listdir(images_path) if not commit.endswith(".txt")]
    if sys.argv[2] in commits:
        checkout_commits()
    elif sys.argv[2] in branches_names:
        checkout_branches()
    elif sys.argv[2] == "master":
        checkout_commits()
        checkout_branches()
    else:
        print("Wrong Entry. Please try again.")


def delete_files(org_file_path, untracked_files):
    for file in os.listdir(org_file_path):
        if file != ".wit":
            sub_file = os.path.join(org_file_path, file)
            if os.path.isdir(sub_file):
                delete_files(sub_file, untracked_files)
            else:
                if sub_file not in untracked_files:
                    os.remove(sub_file)


def move_all_files(commit_path, move_to_dir):
    for data in os.walk(commit_path):
        for file in data[2]:
            file_path = os.path.join(data[0], file)
            move_to_path = file_path.replace(commit_path, move_to_dir)
            if r"staging_area\.wit" not in move_to_path:
                if not os.path.exists(move_to_path):
                    if not os.path.exists(os.path.dirname(move_to_path)):
                        x = os.path.dirname(move_to_path)
                        os.mkdir(x)
                    shutil.copy(file_path, os.path.dirname(move_to_path))


def graph():
    work_dir = get_wit_path()["work_dir"]
    images_path = os.path.join(work_dir, ".wit", "images")
    if not os.path.exists(os.path.join(work_dir, ".wit", "references.txt")):
        print("You can't draw a graph without making any backups.")
        return
    branches_dict = get_branches_dict()
    head = branches_dict["HEAD"]
    commit_id = branches_dict["HEAD"]
    master = branches_dict["master"]
    commits = []
    while commit_id != "None":
        commits.append(commit_id)
        with open(os.path.join(images_path, commit_id + ".txt"), "r") as commit_file:
            commit_txt = commit_file.read()
        commit_id = commit_txt[commit_txt.index("=") + 1: commit_txt.index("\n")]
    dot = Digraph(comment='Commits')
    i = 0
    while i < len(commits):
        if i > 0:
            dot.edge(commits[i - 1], commits[i])
        i += 1
    dot.edge("", head, "HEAD")
    if master == head:
        dot.edge(" ", head, "master")
    dot.view()


def branch():
    work_dir = get_wit_path()["work_dir"]
    ref_path = os.path.join(work_dir, ".wit", "references.txt")
    if not os.path.exists(ref_path):
        print("You can't make a branch before you have commits.")
        return 
    if sys.argv[2] in get_branches_dict().keys():
        print("We Already have a branch with that name in here. Please choose another.") 
        return 
    branches_dict = get_branches_dict()
    ref = branches_dict["HEAD"]
    with open(ref_path, "a") as ref_file:
        ref_file.write(f"{sys.argv[2]}={ref}\n")


def merge():
    work_dir = get_wit_path()["work_dir"]
    branch_name = sys.argv[2]
    branches_dict = get_branches_dict()
    branches_lst = list(branches_dict.keys())
    branches_lst.remove("HEAD")
    branches_lst.remove("master")
    if branch_name not in branches_lst:
        print("Wrong branch. Please try again.")
        return 
    head_commit = branches_dict["HEAD"]
    branch_commit = branches_dict[sys.argv[2]]
    head_parents = line_commit(head_commit)
    branch_parents = line_commit(branch_commit)
    common_commits = head_parents.intersection(branch_parents)
    base_commit = common_commits.pop()
    copy_missing_files(base_commit, branch_commit)
    copy_changed_files(base_commit, branch_commit)
    commit()
    branches_dict = get_branches_dict()
    new_commit_id = branches_dict["HEAD"]
    date_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    with open(os.path.join(work_dir, ".wit", "images", new_commit_id + ".txt"), "w") as commit_txt:
        commit_txt.write(f"parent={branch_commit}, {head_commit}\ndate={date_time}\nmessage={sys.argv[2]}")


def copy_missing_files(base_commit, branch_commit):
    work_dir = get_wit_path()["work_dir"]
    branch_commit_path = os.path.join(work_dir, ".wit", "images", branch_commit)
    staging_area_path = os.path.join(work_dir, ".wit", "staging_area")
    for data in os.walk(branch_commit_path):
        for file in data[2]:
            file_path_in_branch_commit = os.path.join(data[0], file)
            file_path_in_base_commit = file_path_in_branch_commit.replace(branch_commit, base_commit)
            if not os.path.exists(file_path_in_base_commit):
                move_f(file_path_in_branch_commit, os.path.join(staging_area_path, file))


def copy_changed_files(base_commit, branch_commit):
    work_dir = get_wit_path()["work_dir"]
    branch_commit_path = os.path.join(work_dir, ".wit", "images", branch_commit)
    staging_area_path = os.path.join(work_dir, ".wit", "staging_area")
    for data in os.walk(branch_commit_path):
        if ".wit" not in data[0]:
            for file in data[2]:
                file_path_in_branch_commit = os.path.join(data[0], file)
                file_path_in_base_commit = file_path_in_branch_commit.replace(branch_commit, base_commit)
                if os.path.exists(file_path_in_base_commit):
                    cmp1 = filecmp.cmp(file_path_in_branch_commit, file_path_in_base_commit)
                    if not cmp1:
                        file_path_in_staging = file_path_in_branch_commit.replace(branch_commit_path, staging_area_path)
                        os.remove(file_path_in_staging)
                        move_f(file_path_in_branch_commit, file_path_in_staging)


def line_commit(commit_id):
    work_dir = get_wit_path()["work_dir"]
    commits = set()
    while commit_id != "None":
        commits.add(commit_id)
        with open(os.path.join(work_dir, ".wit", "images", commit_id + ".txt"), "r") as commit_file:
            content = commit_file.read()
        commit_id = content[content.index("=") + 1: content.index("\n")]
    return commits
    

def main():
    if len(sys.argv) < 2:
        print("You must also choose a funcion to use.")
        return
    if sys.argv[1] == "init":
        init()
    elif sys.argv[1] == "add":
        if len(sys.argv) != 3:
            print("The function 'add' requires you to insert a file or a directory.")
            return
        add()
    elif sys.argv[1] == "commit":
        if len(sys.argv) != 3:
            print("The function 'commit' requires you to insert a name for the commit.")
            return
        commit()
    elif sys.argv[1] == "status":
        if len(sys.argv) != 2:
            print("The function 'status' can have no other entries.")
            return
        status()
    elif sys.argv[1] == "remove":
        if len(sys.argv) != 3:
            print("The function 'remove' requires you to insert a file or a directory to delete.")
            return
        remove()
    elif sys.argv[1] == "checkout":
        if len(sys.argv) != 3:
            print("The function 'checkout' requires you to insert a commit id.")
            return
        checkout()
    elif sys.argv[1] == "graph":
        if len(sys.argv) != 2:
            print("The function 'graph' can have no other entries.")
            return
        graph()
    elif sys.argv[1] == "branch":
        if len(sys.argv) != 3:
            print("The function 'branch' requires you to eneter a branch.")
            return
        branch()
    elif sys.argv[1] == "merge":
        if len(sys.argv) != 3:
            print("The function 'merge' requires you to eneter a branch.")
            return
        merge()
    else:
        print("You didn't choose any of the function in this file.")


if __name__ == "__main__":
    main()