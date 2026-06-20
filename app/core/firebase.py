# import firebase_admin
# from firebase_admin import credentials, messaging
#
# # Firebase ko initialize karna (Sirf ek baar)
# if not firebase_admin._apps:
#     cred = credentials.Certificate("serviceAccountKey.json")
#     firebase_admin.initialize_app(cred)
#
# def send_push_notification(token: str, title: str, body: str):
#     """
#     Ye function kisi bhi specific FCM token par notification bhejta hai.
#     """
#     try:
#         message = messaging.Message(
#             notification=messaging.Notification(
#                 title=title,
#                 body=body,
#             ),
#             token=token,
#         )
#         # Notification send karein
#         response = messaging.send(message)
#         print(f"Successfully sent notification: {response}")
#         return True
#     except Exception as e:
#         print(f"FCM Error: {e}")
#         return False