def get_tree_max_id(value, list_id=[]):
    """
    得到最大Tree max id
    """
    if not value:
        return 0  # the first node id

    if isinstance(value, list):
        for content in value:  # content -> dict
            try:
                children = content['children']
            except KeyError:
                """
                待返回错误信息
                """
                pass

            if children:
                get_tree_max_id(children)

            list_id.append(content['id'])

    return max(list_id)


def get_file_size(size):
    """计算大小
    """

    if size >= 1048576:
        size = str(round(size / 1048576, 2)) + 'MB'
    elif size >= 1024:
        size = str(round(size / 1024, 2)) + 'KB'
    else:
        size = str(size) + 'Byte'

    return size

def getNodeIdList(nodeId,treeBody):
    nodeList = []
    for each in treeBody:
        if(each['id'] == int(nodeId)):
            nodeList.append(each['id'])
            if(len(each['children'])>0):
                nodeList.extend(getAllChildId(each['children']))
            break
        else:
            nodeList.extend(getNodeIdList(nodeId,each['children']))
    return nodeList

def getAllChildId(treeList):
    nodeList = []
    for each in treeList:
        nodeList.append(each['id'])
        if(isinstance(each['children'],list) and len(each['children'])>0):
            nodeList.extend(getAllChildId(each['children']))
    return nodeList
