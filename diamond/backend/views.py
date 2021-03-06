from django.shortcuts import render
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from login.views import authentication
from datetime import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
import hashlib

# my models
from .models import User, Document, Team, TeamUser, Comment, Collection, Delete_document, Template, Browsing
# third-party
from notifications.models import Notification
from notifications.signals import notify


# 会在文档类被创建的时候触发
@receiver(post_save, sender=Document)
def hash_document_key(sender, instance=None, created=False, **kwargs):
    if created:
        # print("hash document !")
        raw_code = instance.key.encode('utf-8')
        # 生成哈希加密后的identifier
        md = hashlib.md5()
        md.update(raw_code)
        instance.key = md.hexdigest()
        instance.save()


def transfer(key):
    doc = Document.objects.get(key=key)
    doc_id = doc.pk
    return doc_id


# 删除文档
def delete_doc(request):
    print("delete doc")
    key = request.POST.get("doc_id")
    doc_id = transfer(key)
    user = authentication(request)
    try:
        doc = Document.objects.get(pk=doc_id)
        delete_doc = Delete_document.objects.create(creator=doc.creator, team=doc.team, in_group=doc.in_group,
                                                    name=doc.name, content=doc.content,
                                                    created_date=doc.created_date, modified_date=doc.modified_date)
        doc.delete()
        data = {'flag': "yes", 'delete_doc_id': delete_doc.pk}
        print("success")
    except expression as identifier:
        data = {'flag': "no"}
    return JsonResponse(data)


# 拉取已被删除在回收站的文档
def get_deleted_docs(request):
    print("get deleted docs")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    deleted_documents = Delete_document.objects.filter(creator=user)
    deleted_docs = []
    for doc in deleted_documents:
        item = {
            'name': doc.name,
            'doc_id': doc.pk,
        }
        deleted_docs.append(item)
    data = {'deleted_docs': deleted_docs}
    return JsonResponse(data)


# 还原文件
def restore_doc(request):
    print("restore")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    delete_doc_id = request.POST.get("doc_id")
    delete_doc = Delete_document.objects.get(pk=delete_doc_id)
    data = {'flag': "no"}
    if user == delete_doc.creator:
        # 生成独特的原始码
        name = delete_doc.name
        key = user.username + name + str(datetime.now())
        doc = Document.objects.create(creator=delete_doc.creator, team=delete_doc.team, in_group=delete_doc.in_group,
                                      name=delete_doc.name, key=key,
                                      content=delete_doc.content, created_date=delete_doc.created_date,
                                      modified_date=delete_doc.modified_date)
        delete_doc.delete()
        data = {'flag': "yes", 'doc_id': doc.key}
    return JsonResponse(data)


# 彻底删除文件
def delete_doc_completely(request):
    print("delete doc completely")
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    delete_doc_id = request.POST.get("doc_id")
    delete_doc = Delete_document.objects.get(pk=delete_doc_id)
    data = {'flag': "no"}
    if user == delete_doc.creator:
        delete_doc.delete()
        data = {'flag': "yes"}
    return JsonResponse(data)


# 收藏文件
def collect_doc(request):
    print("collect doc")
    key = request.POST.get("doc_id")
    doc_id = transfer(key)
    # print(doc_id)
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    doc = Document.objects.get(pk=doc_id)
    data = {'flag': "no", 'msg': "already collected"}
    if not Collection.objects.filter(Q(user=user) & Q(doc=doc)):
        Collection.objects.create(user=user, doc=doc)
        data = {'flag': "yes", 'msg': "collect success"}
    # print("success")
    return JsonResponse(data)


# 取消收藏
def uncollect_doc(request):
    print("uncollect doc")
    key = request.POST.get("doc_id")
    doc_id = transfer(key)
    # print(doc_id)
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    doc = Document.objects.get(pk=doc_id)
    collection = Collection.objects.get(Q(user=user) & Q(doc=doc))
    collection.delete()
    data = {'flag': "yes", 'msg': "uncollect success"}
    # print("success")
    return JsonResponse(data)


# 新建文档
def create_doc(request):
    print('create doc')
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    name = request.POST.get("title")
    team_id = request.POST.get("team_id")
    in_group = False
    team = None
    if int(team_id) >= 0:
        in_group = True
        team = Team.objects.get(id=team_id)
    # content = request.POST.get("content")
    # create_time = request.POST.get("create_time")
    # print(content)

    # 生成独特的原始码
    key = user.username + name + str(datetime.now())
    # 创建一个新文档, 并且保存时触发trigger，生成hash code
    doc = Document.objects.create(creator=user, name=name, in_group=in_group, team=team, key=key)

    # print(doc.pk)
    data = {'flag': "yes", 'doc_id': doc.key, 'msg': "create success"}
    # print("success")
    return JsonResponse(data)


# 重命名
def rename_doc(request):
    print('rename doc')
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    key = request.POST.get("doc_id")
    doc_id = transfer(key)
    doc_name = request.POST.get("title")
    doc = Document.objects.get(pk=doc_id)
    doc.name = doc_name
    doc.save()
    data = {'flag': True, 'msg': "rename success"}
    # print("success")
    return JsonResponse(data)


# 用模板新建文件
def create_doc_with_temp(request):
    print('create doc with template')
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    name = request.POST.get("title")
    team_id = request.POST.get("team_id")
    temp_id = request.POST.get("temp_id")
    print(temp_id)
    in_group = False
    team = None
    if (int(team_id) >= 0):
        in_group = True
        team = Team.objects.get(id=team_id)
    # create_time = request.POST.get("create_time")
    key = user.username + name + str(datetime.now())
    # 保存时会调用signal生成hash
    doc = Document.objects.create(creator=user, name=name, in_group=in_group, team=team, key=key)
    temp = Template.objects.get(pk=temp_id)
    temp_content = temp.content
    doc.content = temp_content
    doc.save()
    data = {'flag': "yes", 'doc_id': doc.key, 'msg': "create success"}
    return JsonResponse(data)


# 保存文档内容
def save_doc(request):
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    print('save doc')
    content = request.POST.get("content")
    key = request.POST.get("doc_id")
    doc_id = transfer(key)
    # create_time = request.POST.get("modified_time")
    doc = Document.objects.get(pk=doc_id)
    doc.content = content
    doc.save()
    data = {'flag': "yes", 'msg': "modified success"}
    # print("success")
    return JsonResponse(data)


# 获取文档内容及收藏状态 TODO: is like
def get_doc(request):
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    # 还需判断该用户权限
    # print("get doc")
    key = request.POST.get("doc_id")
    # print("key")
    # print(key)
    doc_id = transfer(key)
    team_id = int(request.POST.get("team_id"))
    doc = Document.objects.get(pk=doc_id)
    if not Collection.objects.filter(Q(user=user) & Q(doc=doc)):
        islike = False
    else:
        islike = True

    if team_id != -1:  # 如果是团队文档， 团队文档不能分享
        team = Team.objects.get(id=team_id)
        try:  # 如果访问者是团队成员
            team = Team.objects.get(id=team_id)
            team_user = TeamUser.objects.get(user=user, team=team)
            level = team_user.permission_level
            data = {'name': doc.name, 'content': doc.content, 'islike': islike, 'level': level}
            return JsonResponse(data)
        except:
            return HttpResponse('Unauthorized', status=401)
    else:  # 如果是个人文档
        if doc.creator == user:  # 如果访问者是创建者
            print("访问者是创建者")
            data = {'name': doc.name, 'content': doc.content, 'islike': islike, 'level': 4}
            return JsonResponse(data)
        else:  # 如果访问者是其他人，获取文档的share level
            print("访问者是其他人")
            level = doc.share_level
            print("share level", level)
            if level == 1:  # 如果share level为1，禁止访问
                print("禁止方问")
                return HttpResponseForbidden()
            data = {'name': doc.name, 'content': doc.content, 'islike': islike, 'level': level}
            return JsonResponse(data)

    # team_id = request.POST.get("team_id")
    # print(doc_id)
    # team = None
    # if team_id != -1:
    # team = Team.objects.get(pk=team_id)
    # islike = True
    # print("success")


# 拉取最近浏览，我创建和收藏的文档信息
def my_doc(request):
    # print('my docs')
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    created_documents = Document.objects.filter(creator=user)
    created_docs = []
    collections = Collection.objects.filter(user=user)
    collected_docs = []
    browsing = Browsing.objects.filter(user=user)
    browsing_docs = []
    # 我创建的
    for d in created_documents:
        if not d.in_group:
            c_item = {
                'name': d.name,
                # 'content': d.content,
                'doc_id': d.key,
                'created_time': d.created_date.__format__('%Y-%m-%d %H:%M'),
            }
            created_docs.append(c_item)
    # 我收藏的
    for d in collections:
        if not d.doc.in_group:
            c_item = {
                'name': d.doc.name,
                # 'content': d.content,
                'doc_id': d.doc.key,
                'collected_time': d.collected_date.__format__('%Y-%m-%d %H:%M'),
            }
            collected_docs.append(c_item)
    # 最近浏览
    for d in browsing:
        if d.doc.in_group:
            team = d.doc.team
            team_user = TeamUser.objects.get(user=user, team=team)
            c_item = {
                'name': d.doc.name,
                'doc_id': d.doc.key,
                'in_group': True,
                'team_id': team.pk,
                'level': team_user.permission_level,
                'browse_time': d.browsing_date.__format__('%Y-%m-%d %H:%M'),
            }
        else:
            c_item = {
                'name': d.doc.name,
                'doc_id': d.doc.key,
                'in_group': False,
                'team_id': -1,
                'level': 4,
                'browse_time': d.browsing_date.__format__('%Y-%m-%d %H:%M'),
            }
        browsing_docs.append(c_item)
    data = {'browsing_docs': browsing_docs, 'created_docs': created_docs, 'collected_docs': collected_docs}
    return JsonResponse(data)


def edit_share_level(request):
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    key = request.POST.get('doc_id')
    doc_id = transfer(key)
    level = request.POST.get('level')
    print("edit share level", level)
    doc = Document.objects.get(id=doc_id)
    doc.share_level = level
    doc.save()
    return JsonResponse({})


def get_doc_key(request):
    key = request.POST.get('doc_id')
    doc_id = transfer(key)
    doc = Document.objects.get(id=doc_id)
    data = {"share_level": str(doc.share_level)}
    return JsonResponse(data)


# 新建、更新浏览记录
def update_browsing(request):
    # print('update browsing')
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    key = request.POST.get("doc_id")
    doc_id = transfer(key)
    doc = Document.objects.get(pk=doc_id)
    oldb = Browsing.objects.filter(Q(user=user) & Q(doc=doc))
    if oldb:
        oldb.delete()
    newb = Browsing.objects.create(user=user, doc=doc)
    data = {"message": 1}
    return JsonResponse(data)


# 搜索个人文档
def doc_search(request):
    user = authentication(request)
    if user is None:
        return HttpResponse('Unauthorized', status=401)
    keyword = request.POST.get("keyword")
    search_doc = Document.objects.filter(Q(creator=user) & Q(name__icontains=keyword))
    docs = []
    for d in search_doc:
        c_item = {
            'name': d.name,
            'doc_id': d.key,
            'created_time': d.created_date.__format__('%Y-%m-%d %H:%M'),
        }
        docs.append(c_item)
    return JsonResponse({'docs': docs})


def get_lock(request):
    key = request.POST.get('doc_id')
    doc_id = transfer(key)
    doc = Document.objects.get(id=doc_id)
    data = {"success": False}
    if doc.is_locked:
        print("文章已被上锁，用户不能进入！")
    else:

        print("文章未上锁，用户可以进入")
        doc.is_locked = True
        data["success"] = True
    doc.save()
    return JsonResponse(data)


def unlock(request):
    print("文件解锁！")
    key = request.POST.get('doc_id')
    doc_id = transfer(key)
    doc = Document.objects.get(id=doc_id)
    doc.is_locked = False
    doc.save()
    return JsonResponse({})

# # 搜索团队文档
# def team_doc_search(request):
#     user = authentication(request)
#     if user is None:
#         return HttpResponse('Unauthorized', status=401)
#     keyword = request.POST.get("keyword")
#     belong_team = TeamUser.objects.filter(user=user)
#     if not belong_team:
#         return JsonResponse({'flag': 0, 'message': '无团队'})
#     team_sdoc = []
#     for d in belong_team:
#         team = d.team
#         team_docs = Document.objects.filter(team=team)
#         for e in team_docs:
#             c_item = {
#                 'name': e.name,
#                 'team': e.team,
#                 'doc_id': e.key
#             }
#             team_docs.append(c_item)
#     return JsonResponse({'team_docs': team_sdoc})
