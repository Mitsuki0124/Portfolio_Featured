import maya.cmds as cmds


def create_joints_along_curve(num_joints=5, create_chain=True, orient_joints=True, delete_temp_curve=False):
    """
    選択したカーブ、または選択したエッジから生成したカーブに沿ってジョイントを作成します。
    """
    selection = cmds.ls(selection=True) or []
    if not selection:
        cmds.warning("カーブ、またはメッシュのエッジを選択してください。")
        return

    curve = None
    is_temp_curve = False

    # エッジ選択の場合はカーブに変換
    if ".e[" in selection[0]:
        temp_curve = cmds.polyToCurve(form=2, degree=3, conformToEdgeLoops=True)
        if temp_curve:
            curve = temp_curve[0]
            is_temp_curve = True
        else:
            cmds.warning("エッジからカーブを作成できませんでした。")
            return
    else:
        # カーブオブジェクト自体が選択されているか確認
        shapes = cmds.listRelatives(selection[0], shapes=True) or []
        if shapes and cmds.nodeType(shapes[0]) in ["nurbsCurve"]:
            curve = selection[0]
        else:
            cmds.warning("NURBSカーブまたはメッシュのエッジを選択してください。")
            return

    if num_joints < 2:
        cmds.warning("ジョイント数は2以上に設定してください。")
        return

    # コマンド直接呼び出しでカーブ上の座標を取得
    created_joints = []
    cmds.select(clear=True)

    for i in range(num_joints):
        u_param = float(i) / float(num_joints - 1)

        # cmds.pointOnCurve を使用して座標を直接取得 (turnOnPercentage=True で 0.0〜1.0 指定)
        pos = cmds.pointOnCurve(curve, pr=u_param, turnOnPercentage=True, position=True)

        # ジョイント生成
        cmds.select(clear=True)
        jnt = cmds.joint(position=pos)
        created_joints.append(jnt)

    # 階層化（Chain化）
    if create_chain:
        for i in range(len(created_joints) - 1, 0, -1):
            cmds.parent(created_joints[i], created_joints[i - 1])

        # ジョイントの向きを揃える（Orient Joint）
        if orient_joints:
            cmds.select(created_joints[0], replace=True)
            cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)
            # 末端のジョイントの回転をクリア
            cmds.joint(created_joints[-1], edit=True, orientJoint="none")

    # 一時カーブの削除判定
    if is_temp_curve or delete_temp_curve:
        cmds.delete(curve)

    cmds.select(created_joints[0] if create_chain else created_joints, replace=True)
    print(f"カーブに沿って {len(created_joints)} 個のジョイントを作成しました。")


# =========================================================
# GUI
# =========================================================

def build_curve_joint_gui():
    window_name = "createJointsAlongCurveWindow"

    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(window_name, title="沿わせてジョイント生成", widthHeight=(300, 220), sizeable=True)

    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnOffset=["both", 10])

    cmds.text(label="カーブ/エッジに沿ってジョイントを生成", height=30, font="boldLabelFont")
    cmds.separator(style="in")

    # 入力項目
    num_joints_field = cmds.intSliderGrp(
        label="ジョイント数: ", field=True, minValue=2, maxValue=50, fieldMinValue=2, fieldMaxValue=200, value=5
    )
    chain_cb = cmds.checkBox(label="ジョイントを階層化（Parent）する", value=True)
    orient_cb = cmds.checkBox(label="向きを自動設定（Orient Joint）", value=True)

    cmds.separator(style="none", height=5)

    # 実行ボタン
    def on_execute(*args):
        num = cmds.intSliderGrp(num_joints_field, query=True, value=True)
        chain = cmds.checkBox(chain_cb, query=True, value=True)
        orient = cmds.checkBox(orient_cb, query=True, value=True)
        create_joints_along_curve(num_joints=num, create_chain=chain, orient_joints=orient)

    cmds.button(label="生成実行", height=35, command=on_execute, backgroundColor=[0.3, 0.5, 0.4])

    cmds.showWindow(window)


build_curve_joint_gui()
