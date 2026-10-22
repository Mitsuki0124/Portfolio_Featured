import re
from maya import cmds


# =========================================================
# Core Joint Functions
# =========================================================

def get_selected_joints():
    """選択中のノードからJointのみを取得"""
    selection = cmds.ls(selection=True, dag=True, long=True) or []
    return [node for node in selection if cmds.nodeType(node) == "joint"]


def joint_name_display():
    """選択したJointの名前をビューポートに表示"""
    joints = get_selected_joints()
    if not joints:
        cmds.warning("Jointを選択してください。")
        return

    for joint in joints:
        short_name = joint.split("|")[-1]
        cmds.setAttr(joint + ".drawLabel", 1)
        cmds.setAttr(joint + ".type", 18)  # 18 = Custom
        cmds.setAttr(joint + ".otherType", short_name, type="string")

    print(f"{len(joints)} 個のJointの名前を表示しました。")


def joint_hierarchy_select():
    """選択したJoint（または親）以下のすべてのJointを階層選択"""
    selection = cmds.ls(selection=True, long=True) or []
    if not selection:
        cmds.warning("Jointまたは親ノードを選択してください。")
        return

    all_joints = cmds.listRelatives(selection, allDescendents=True, type="joint", fullPath=True) or []
    for node in selection:
        if cmds.nodeType(node) == "joint":
            all_joints.append(node)

    all_joints = list(dict.fromkeys(all_joints))

    if all_joints:
        cmds.select(all_joints, replace=True)
        print(f"{len(all_joints)} 個のJointを階層選択しました。")
    else:
        cmds.warning("選択配下にJointが見つかりませんでした。")


def joint_name_delete():
    """シーン内のすべてのJointの名前表示をオフ"""
    joints = cmds.ls(type="joint") or []
    count = 0
    for joint in joints:
        if cmds.attributeQuery("drawLabel", node=joint, exists=True):
            if cmds.getAttr(joint + ".drawLabel"):
                cmds.setAttr(joint + ".drawLabel", 0)
                count += 1

    print(f"{count} 個のJointの名前表示を削除（非表示）しました。")


# =========================================================
# Feature 1: Color Coding
# =========================================================

def color_code_joints(reset=False):
    """L / R プレフィックスに応じてJointの表示色を設定"""
    joints = get_selected_joints()
    if not joints:
        joints = cmds.ls(type="joint", long=True) or []

    if not joints:
        cmds.warning("Jointが見つかりませんでした。")
        return

    for joint in joints:
        if reset:
            cmds.setAttr(joint + ".overrideEnabled", 0)
            continue

        short_name = joint.split("|")[-1]
        cmds.setAttr(joint + ".overrideEnabled", 1)
        cmds.setAttr(joint + ".overrideRGBColors", 0)

        if re.search(r"^(L_|Left_)", short_name, re.IGNORECASE):
            cmds.setAttr(joint + ".overrideColor", 6)   # 青
        elif re.search(r"^(R_|Right_)", short_name, re.IGNORECASE):
            cmds.setAttr(joint + ".overrideColor", 13)  # 赤
        else:
            cmds.setAttr(joint + ".overrideColor", 17)  # 黄

    if reset:
        print("Jointの色指定をリセットしました。")
    else:
        print(f"{len(joints)} 個のJointを自動色分けしました（L:青 / R:赤 / C:黄）。")


# =========================================================
# Feature 2: Renumbering Suffix
# =========================================================

def renumber_joint_suffix(padding_field):
    """選択順または階層順に末尾の数字を綺麗に振り直す"""
    selection = cmds.ls(selection=True, long=True) or []
    if not selection:
        cmds.warning("Jointを選択してください。")
        return

    joints = []
    for node in selection:
        if cmds.nodeType(node) == "joint":
            joints.append(node)
        descendants = cmds.listRelatives(node, allDescendents=True, type="joint", fullPath=True) or []
        descendants.reverse()
        for desc in descendants:
            if desc not in joints:
                joints.append(desc)

    padding = cmds.intField(padding_field, query=True, value=True)

    renamed_count = 0
    for idx, joint in enumerate(joints, start=1):
        short_name = joint.split("|")[-1]
        match = re.search(r"^(.*?)(\d+)$", short_name)
        if match:
            base_name = match.group(1)
        else:
            base_name = short_name + "_"

        new_number_str = str(idx).zfill(padding)
        new_name = f"{base_name}{new_number_str}"

        if short_name != new_name:
            cmds.rename(joint, new_name)
            renamed_count += 1

    print(f"{renamed_count} 個のJointのナンバリングを振り直しました。")


# =========================================================
# Feature 3: Duplicate Name Check & Fix
# =========================================================

def find_duplicate_joints():
    """重複名を持つJointを抽出"""
    joints = cmds.ls(type="joint", long=True) or []
    name_map = {}

    for jnt in joints:
        short_name = jnt.split("|")[-1]
        name_map.setdefault(short_name, []).append(jnt)

    duplicates = []
    for short_name, paths in name_map.items():
        if len(paths) > 1:
            duplicates.extend(paths)

    return duplicates


def highlight_duplicate_joints():
    """重複名を持つJointをビューポートで選択"""
    duplicates = find_duplicate_joints()
    if duplicates:
        cmds.select(duplicates, replace=True)
        cmds.warning(f"{len(duplicates)} 個の重複名Jointが見つかりました。選択を表示します。")
    else:
        cmds.select(clear=True)
        print("重複名を持つJointはありません。クリアです！")


def fix_duplicate_joints():
    """重複名を持つJointを自動リネーム（_dup1, _dup2... を付与）"""
    duplicates = find_duplicate_joints()
    if not duplicates:
        print("修正対象の重複名Jointはありません。")
        return

    renamed_count = 0
    # 親階層が深い（フルパスが長い）順に処理してパス崩れを防ぐ
    duplicates.sort(key=lambda x: len(x.split("|")), reverse=True)

    for jnt in duplicates:
        if not cmds.objExists(jnt):
            continue
        
        short_name = jnt.split("|")[-1]
        # 同名ノードがまだ存在するか確認
        if len(cmds.ls(short_name)) > 1:
            new_name = f"{short_name}_dup1"
            index = 1
            while cmds.objExists(new_name):
                index += 1
                new_name = f"{short_name}_dup{index}"
            
            cmds.rename(jnt, new_name)
            renamed_count += 1

    print(f"{renamed_count} 個の重複名Jointを自動リネームしてユニーク化しました。")


# =========================================================
# Feature 4: Empty Transform Cleanup
# =========================================================

def get_empty_transforms():
    """階層内の不要な空Transformノードを検索"""
    selection = cmds.ls(selection=True, long=True) or []
    if selection:
        nodes = cmds.listRelatives(selection, allDescendents=True, type="transform", fullPath=True) or []
        for sel in selection:
            if cmds.nodeType(sel) == "transform":
                nodes.append(sel)
    else:
        nodes = cmds.ls(type="transform", long=True) or []

    empty_transforms = []
    for node in nodes:
        if cmds.nodeType(node) != "transform":
            continue

        # シェイプまたは子ノードが存在するか確認
        children = cmds.listRelatives(node, children=True, fullPath=True) or []
        if not children:
            empty_transforms.append(node)

    return empty_transforms


def find_empty_transforms():
    """空Transformノードを選択"""
    empty_nodes = get_empty_transforms()
    if empty_nodes:
        cmds.select(empty_nodes, replace=True)
        cmds.warning(f"{len(empty_nodes)} 個の空Transformノードが見つかりました。")
    else:
        cmds.select(clear=True)
        print("空のTransformノードは見つかりませんでした。")


def delete_empty_transforms():
    """空Transformノードを一括削除"""
    empty_nodes = get_empty_transforms()
    if not empty_nodes:
        print("削除対象の空Transformノードはありません。")
        return

    # 親階層が深い順にソートして削除
    empty_nodes.sort(key=lambda x: len(x.split("|")), reverse=True)
    count = 0
    for node in empty_nodes:
        if cmds.objExists(node):
            cmds.delete(node)
            count += 1

    print(f"{count} 個の不要な空Transformノードを削除しました。")


# =========================================================
# GUI
# =========================================================

def joint_name_tool():
    window_name = "jointNameToolWindow"

    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(
        window_name, title="Joint Name Tool Pro", widthHeight=(320, 520), sizeable=True
    )

    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)

    cmds.text(label="Joint Name Tool Pro", height=35, font="boldLabelFont")
    cmds.separator(height=10, style="in")

    # 1. Display & Selection
    cmds.frameLayout(
        label="Name Display & Selection", collapsable=False, marginWidth=10, marginHeight=10
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    cmds.button(label="Joint Name Display", height=30, command=lambda x: joint_name_display())
    cmds.button(label="Joint Hierarchy Select", height=30, command=lambda x: joint_hierarchy_select())
    cmds.button(label="Delete Joint Names", height=30, command=lambda x: joint_name_delete())
    cmds.setParent("..")
    cmds.setParent("..")

    # 2. Color Coding
    cmds.frameLayout(
        label="L / R Color Coding", collapsable=True, collapse=False, marginWidth=10, marginHeight=10
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    cmds.button(label="Auto Color (L:Blue / R:Red)", height=30, command=lambda x: color_code_joints(reset=False))
    cmds.button(label="Reset Colors", height=25, command=lambda x: color_code_joints(reset=True))
    cmds.setParent("..")
    cmds.setParent("..")

    # 3. Renumbering
    cmds.frameLayout(
        label="Auto Renumbering Suffix", collapsable=True, collapse=False, marginWidth=10, marginHeight=10
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 100), adjustableColumn=2)
    cmds.text(label="Digits (Padding): ")
    padding_field = cmds.intField(value=2, minValue=1, maxValue=5)
    cmds.setParent("..")
    cmds.button(
        label="Renumber Selected Suffix",
        height=30,
        command=lambda x: renumber_joint_suffix(padding_field)
    )
    cmds.setParent("..")
    cmds.setParent("..")

    # 4. Check & Cleanup Tools
    cmds.frameLayout(
        label="Check & Cleanup Tools", collapsable=True, collapse=False, marginWidth=10, marginHeight=10
    )
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    
    # Duplicate Check
    cmds.text(label="-- Duplicate Joint Names --", align="center")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(135, 135))
    cmds.button(label="Highlight Duplicates", height=28, width=135, command=lambda x: highlight_duplicate_joints())
    cmds.button(label="Fix Duplicates", height=28, width=135, command=lambda x: fix_duplicate_joints())
    cmds.setParent("..")

    # Cleanup Empty Transforms
    cmds.text(label="-- Empty Transforms --", align="center")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(135, 135))
    cmds.button(label="Find Empty", height=28, width=135, command=lambda x: find_empty_transforms())
    cmds.button(label="Delete Empty", height=28, width=135, command=lambda x: delete_empty_transforms())
    cmds.setParent("..")

    cmds.setParent("..")
    cmds.setParent("..")

    cmds.showWindow(window)


joint_name_tool()
