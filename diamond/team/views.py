from django.shortcuts import render
from django.db.models import Q
from backend.models import User, Team, TeamUser, Document
from login.views import authentication
from django.http import JsonResponse, HttpResponse


# Create your views here.
# 新建团队
def create_team(request):
    print('create team')
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_name = request.POST.get("name")
    team = Team.objects.create(team_name=team_name)
    TeamUser.objects.create(team=team, user=user, is_leader=True, permission_level=4)
    return JsonResponse({})


# 搜索用户
def search_user(request):
    print('search user')
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    name = request.POST.get("name")
    team_id = request.POST.get("team_id")
    team = Team.objects.get(id=team_id)
    # print("key word", name)
    if name == "":
        users = User.objects.all()
    else:
        users = User.objects.filter(
            Q(username__icontains=name)
        )
    user_list = []
    for user in users:
        try:
            relation = TeamUser.objects.get(user=user, id=team_id)
            if relation.is_leader:
                continue
            is_join = True
        except:
            is_join = False
        item = {"username": user.username, "password": user.password, "wechat": user.wechat,
                "phone_number": user.phone_number, "email": user.email, "is_join": is_join}
        user_list.append(item)
    data = {"user_list": user_list}

    return JsonResponse(data)


def is_leader(request):
    print("current user is leader?")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_id = request.POST.get("team_id")
    team = Team.objects.get(id=team_id)
    # print("team id")
    # print(team_id)
    team_user = TeamUser.objects.get(team=team, user=user)
    data = {"is_leader": team_user.is_leader, "level": team_user.permission_level}
    return JsonResponse(data)


# 拉取用户所有的团队
def get_my_team(request):
    # print('get my team')
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_user = TeamUser.objects.filter(user=user)
    team_list = []
    for relation in team_user:
        item = {'team_name': relation.team.team_name, 'team_id': relation.team.id,
                "introduction": relation.team.introduction, "is_leader": relation.is_leader,
                "level": relation.permission_level}
        team_list.append(item)
    data = {"team_list": team_list}
    return JsonResponse(data)


def delete_my_team(request):
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_id = request.POST.get("team_id")
    print(team_id)
    team = Team.objects.get(id=team_id)
    team.delete()
    return JsonResponse({})


# 拉取某团队队内成员
def get_team_member(request):
    print("get team list")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_id = request.POST.get("team_id")
    team = Team.objects.get(id=team_id)
    team_user = TeamUser.objects.filter(team=team)
    user_list = []
    for relation in team_user:
        if relation.is_leader:
            continue
        target_user = relation.user
        team_user = TeamUser.objects.get(user=target_user, team=team)
        item = {'username': target_user.username, "level": str(team_user.permission_level)}
        user_list.append(item)
    # fake_list = [{'username': "aa", "level": "1"}, {'username': "bb", "level": "2"}, {'username': "cc", "level": "3"}]
    data = {'user_list': user_list}
    return JsonResponse(data)


# 邀请团队成员,强制邀请 TODO 使用消息通知实现
def add_team_member(request):
    print("add team member")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_id = request.GET.get("team_id")
    team = Team.objects.get(id=team_id)
    TeamUser.objects.create(team=team, user=user, is_leader=False)
    return JsonResponse({})


# 退出团队
def exit_team(request):
    print("exit team")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_id = request.POST.get("team_id")
    team = Team.objects.get(id=team_id)
    team_user = TeamUser.objects.get(team=team, user=user)
    team_user.delete()
    return JsonResponse({})


# 删除团队成员
def delete_team_member(request):
    print("delete team member")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_id = request.POST.get("team_id")
    team = Team.objects.get(id=team_id)
    target_username = request.POST.get("username")
    user = User.objects.get(username=target_username)
    team_user = TeamUser.objects.get(team=team, user=user)
    team_user.delete()
    return JsonResponse({})


# modify permission
def modify_permission(request):
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_id = request.POST.get("team_id")
    team = Team.objects.get(id=team_id)
    target_user = request.POST.get("target_user")
    permission_level = request.POST.get("permission_level")
    team_user = TeamUser.objects.get(user=target_user, team=team)
    team_user.permission_level = permission_level
    team_user.save()
    return JsonResponse({})


# 拉取团队的文档信息
def get_team_docs(request):
    print("get team docs")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    team_id = request.POST.get("team_id")
    # print(team_id)
    team = Team.objects.get(pk=team_id)
    # print(team)
    documents = Document.objects.filter(team=team)
    # print(documents)
    docs = []
    for doc in documents:
        item = {
            'name': doc.name,
            # 'content': d.content,
            'doc_id': doc.pk,
        }
        docs.append(item)
    data = {'team_docs': docs}
    return JsonResponse(data)
