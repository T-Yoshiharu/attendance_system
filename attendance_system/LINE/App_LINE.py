import json, requests
from datetime import datetime
# from linebot import LineBotApi
# from linebot.models import TextSendMessage

with open("id.json", "r") as f:
    ids = json.load(f)
token = ids["LINE"]["LINE_token"] # LINEのトークン
group_ID = ids["LINE"]["groupID"] # 送信先グループのID

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}
url = 'https://api.line.me/v2/bot/message/push'

# line_bot_api = LineBotApi(token)


def post(names:str, mode:str):
    keys = [["hold_inTime", "response_in", "in"], ["hold_outTime", "response_out", "out"]]
    now = datetime.now()
    flag = False
    with open("tmp.json") as f:
        d_update = json.load(f)

    data = {
        'to': group_ID,
        'messages': [
            {
                'type': 'text',
                'text': ""
            }
        ]
    }

    match mode:
        case "checkIN":
            i = 0
            data["messages"][0]["text"] = f"メンバーが315に出勤しました\n- \"{names}\""
            if d_update["latest"] == "out":
                flag = True
        case "checkOUT":
            i = 1
            data["messages"][0]["text"] = f"メンバーが315から退勤しました\n- \"{names}\""
            if d_update["latest"] == "in":
                flag = True

    if (d_update[keys[i][0]] == ""):
        flag = True
    else:
        hold = datetime.strptime(d_update[keys[i][0]], '%Y/%m/%d %H:%M:%S')

    if flag or ((now-hold).seconds > 300):
        response = requests.post(url, headers=headers, json=data)
        quoteToken = response.json()["sentMessages"][0]["quoteToken"]

        d_update[keys[i][0]] = now.strftime('%Y/%m/%d %H:%M:%S')
        d_update[keys[i][1]] = quoteToken
        d_update["latest"] = keys[i][2]
        with open('tmp.json', 'w') as f:
            json.dump(d_update, f)

    else:
        data["messages"][0]["text"] = f"- \"{names}\""
        match mode:
            case "checkIN":
                reply = d_update["response_in"]
            case "checkOUT":
                reply = d_update["response_out"]

        data["messages"][0]["quoteToken"] = reply
        requests.post(url, headers=headers, json=data)


# messages = TextSendMessage(text=m)
# line_bot_api.push_message(group_ID, messages=messages)

if __name__ == "__main__":
    post("haru", "checkIN")