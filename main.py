import logging
import gradio as gr
import time
import base64
from agent import AgentWorkflow
from openai.types.responses import ResponseTextDeltaEvent
from dialog import *
from typing import Any, Dict, List


logging.getLogger('chat_manager').setLevel(logging.DEBUG)



def generate_tag(text: str, icon_file: str=None):
    if icon_file:
        with open(icon_file, "rb") as image_file:
            base64_data = base64.b64encode(image_file.read()).decode("utf-8")
        img_content = f'<img src="data:image/gif;base64,{base64_data}" style="width: 20px; height: 20px; margin-left: 8px;">'
    else:
        img_content = ''
    content = f'''
    <div style="display: flex; align-items: center; font-size: 16px; color: #555;">
        <strong>{text}</strong>
        {img_content}
    </div>
    '''
    return content


THINKING = generate_tag('思考中', "icon/thinking.gif")
THINK_DONE = generate_tag('思考完成 ✔')
EXAMPLES = [
    "讲5个笑话",
    "介绍一下宇宙大爆炸",
    "写一篇300字的关于春天的小学生作文",
    "234+5345等于多少？如果再加上6979呢",
    "写一个冒泡排序算法"
]


def add_thinking(chat_history: List[Dict[str, Any]]):
    chat_history.append({'role': 'assistant', 'content': THINKING, 'metadata': {'is_thinking': True}})
    return chat_history


def set_think_done(chat_history: List[Dict[str, Any]]):
    for msg in chat_history:
        metadata = msg.get('metadata')
        metadata = metadata or {}
        if metadata.get('is_thinking', False):
            msg['content'] = THINK_DONE


def convert_conversation_to_agent_messsages(conversation):
    messages = []
    for msg in conversation:
        metadata = msg.get('metadata')
        metadata = metadata or {}
        is_thinking = 'is_thinking' in metadata
        if msg['role'] == 'user' or (msg['role'] == 'assistant' and not is_thinking):
            messages.append({'role': msg['role'], 'content': msg['content']})
    return messages

async def stream_agent_response(agent: AgentWorkflow, chat_history: List[Dict[str, Any]]):
    chat_history.append({'role': 'assistant', 'content': THINKING, 'metadata': {'is_thinking': True}})
    yield chat_history

    input_messages = convert_conversation_to_agent_messsages(chat_history)
    chat_history.append({'role': 'assistant', 'content': ''})
    async for event in agent.stream_events(input=input_messages):
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            chat_history[-1]['content'] += event.data.delta
            yield chat_history
    set_think_done(chat_history)
    yield chat_history


css = """
.radio-container {
    max-height: 632px;
    overflow-y: auto;
}
"""


def build_demo():
    with gr.Blocks(title="Agent Chatbot", css=css) as demo:
        agent = gr.State(value=AgentWorkflow())
        chat_his = gr.State([])
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown(
                    '''
                    # <center>Chatbot Agent Demo<center>
                    <center>Use the chatbot agent demo make your work and life much more efficient.<center>
                    '''
                )
                with gr.Group():
                    with gr.Row():
                        add_dialog = gr.ClearButton(
                            components=[chat_his],
                            icon=r"icon\add_dialog.png",
                            value='新增对话',
                            min_width=5,
                            size="sm"
                        )
                        delete_dialog = gr.Button(
                            icon=r"icon\delete_dialog.png",
                            value='删除对话',
                            min_width=5,
                            size="sm",
                        )
                    dialog_radio = gr.Radio(
                        show_label=False,
                        interactive=True,
                        value=DEFAULT_CONVERSATION_NAME,
                        choices=[DEFAULT_CONVERSATION_NAME],
                        elem_classes="radio-container"
                    )
            with gr.Column(scale=4):
                with gr.Group():
                    chat_name = gr.Textbox(show_label=False,
                                        interactive=True,
                                        value=DEFAULT_CONVERSATION_NAME,
                                        max_length=CONVERSATION_NAME_MAX_LENGTH)
                    chat_bot = gr.Chatbot(type='messages', 
                                        height=700,
                                        value=[],
                                        show_label=False,
                                        show_copy_button=True,
                                        render_markdown=True)
                with gr.Row():
                    prompt = gr.Textbox(placeholder="请输入指令, Shift + Enter 换行, Enter 键发送指令.",
                                        show_label=False)     
            with gr.Row(scale=2):
                with gr.Group():
                    gr.Examples(examples=EXAMPLES, inputs=[prompt])

        # Radio control
        add_dialog.click(
            add_conversation,
            inputs=[chat_name, chat_bot],
            outputs=[chat_name, chat_bot, dialog_radio]
        )

        delete_dialog.click(
            delete_conversation,
            inputs=[chat_name],
            outputs=[chat_name, chat_bot, dialog_radio]
        )

        dialog_radio.select(
            get_selected_conversation_content,
            inputs=[dialog_radio],
            outputs=[chat_name, chat_bot]
        )

        chat_name.blur(
            rename_conversation,
            inputs=[dialog_radio, chat_name],
            outputs=[dialog_radio, chat_name]
        )

        prompt.submit(
            add_conversation_user,
            inputs=[prompt, chat_name, chat_bot],
            outputs=[dialog_radio, prompt, chat_name, chat_bot]
        ).then(
            stream_agent_response,
            inputs=[agent, chat_bot],
            outputs=[chat_bot]
        ).success(
            update_conversation,
            inputs=[chat_name, chat_bot]
        )

        # load histroy
        demo.load(
            get_dialog_radio,
            inputs=[chat_name],
            outputs=[dialog_radio, chat_bot]
        )
    return demo


def auth(username: str, passwd: str):
    # Only validate username
    if re.match(r'^\w{4,16}$', username):
        return True
    else:
        return False


if __name__ == '__main__':
    build_demo().queue().launch(
        inbrowser=True,
        debug=True,
        show_api=False,
        # auth=[("admin", "123456")],
        auth=auth,
        auth_message="欢迎使用 Agent Chatbot, 请输入用户名和密码"
    )
