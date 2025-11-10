import aws_cdk as core
import aws_cdk.assertions as assertions

from ai_powered booking chatbot.ai_powered booking chatbot_stack import AiPoweredBookingChatbotStack

# example tests. To run these tests, uncomment this file along with the example
# resource in ai_powered booking chatbot/ai_powered booking chatbot_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AiPoweredBookingChatbotStack(app, "ai-powered-booking-chatbot")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
