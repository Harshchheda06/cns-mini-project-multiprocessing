import streamlit as st
from PIL import Image
import numpy as np
import base64
import json
from io import BytesIO
import timeit
from concurrent.futures import ProcessPoolExecutor

def rotate180(n):
    bits = "{0:b}".format(n)
    return int(bits[::-1], 2)

def roll_row(args):
    matrix, key, encrypt_flag = args
    direction_multiplier = 1 if encrypt_flag else -1
    for i in range(len(matrix)):
        modulus = np.sum(matrix[i, :, :], axis=1) % 2
        for c in range(matrix.shape[2]):
            matrix[i, :, c] = np.roll(matrix[i, :, c], direction_multiplier * key[i]) if modulus[c] == 0 else np.roll(matrix[i, :, c], -direction_multiplier * key[i])

def roll_column(args):
    matrix, key, encrypt_flag = args
    direction_multiplier = 1 if encrypt_flag else -1
    for i in range(len(matrix[0])):
        modulus = np.sum(matrix[:, i, :], axis=1) % 2
        for c in range(matrix.shape[2]):
            matrix[:, i, c] = np.roll(matrix[:, i, c], direction_multiplier * key[i]) if modulus[c] == 0 else np.roll(matrix[:, i, c], -direction_multiplier * key[i])

def xor_pixels(args):
    matrix, Kr, Kc = args
    m, n, _ = matrix.shape
    for i in range(m):
        for j in range(n):
            xor_operand_1 = Kc[j] if i % 2 == 1 else rotate180(Kc[j])
            xor_operand_2 = Kr[i] if j % 2 == 0 else rotate180(Kr[i])
            matrix[i, j, :] ^= xor_operand_1 ^ xor_operand_2

def encrypt_image(input_image, alpha=8):
    matrix = np.array(input_image)

    m, n, _ = matrix.shape
    key = create_key(m, n, alpha)
    Kr, Kc = key["Kr"], key["Kc"]

    # Convert Kr and Kc to NumPy arrays if needed
    Kr = np.array(Kr)
    Kc = np.array(Kc)

    args_list = [(matrix, Kc, True)] * key["iter_max"]
    with ProcessPoolExecutor() as executor:
        executor.map(roll_row, args_list)
        executor.map(roll_column, args_list)
        executor.map(xor_pixels, [(matrix, Kr, Kc)] * key["iter_max"])

    encrypted_image = Image.fromarray(matrix.astype(np.uint8))

    # Save the key as a downloadable link
    serialized_key = base64.b64encode(json.dumps(key).encode()).decode()
    with open("encryption_key.txt", "w") as key_file:
        key_file.write(serialized_key)

    return encrypted_image

def create_download_link(image, filename):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:file/png;base64,{image_str}" download="{filename}.png">Download {filename}</a>'
    return href

def decrypt_image(encrypted_image, key):
    matrix = np.array(encrypted_image)

    # Reverse the encryption process
    args_list = [(matrix, key["Kr"], key["Kc"], False)] * key["iter_max"]
    with ProcessPoolExecutor() as executor:
        executor.map(xor_pixels, args_list)
        executor.map(roll_column, args_list)
        executor.map(roll_row, args_list)

    decrypted_image = Image.fromarray(matrix.astype(np.uint8))
    return decrypted_image

def create_key(m, n, alpha):
    Kr = [np.random.randint(0, 2 ** alpha - 1) for _ in range(m)]
    Kc = [np.random.randint(0, 2 ** alpha - 1) for _ in range(n)]
    iter_max = 10  # You can adjust this value based on your requirement

    key_dict = {
        "Kr": Kr,
        "Kc": Kc,
        "iter_max": iter_max
    }

    return key_dict

def main():
    st.title("Image Encryption with Rubik's Cube Crypto")

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)

        alpha_value = st.slider("Select alpha value:", min_value=1, max_value=15, value=8)

        encrypt_button = st.button("Encrypt Image")
        decrypt_button = st.button("Decrypt Image")

        if "encrypted_image" not in st.session_state:
            st.session_state.encrypted_image = None

        if encrypt_button:
            # Load the input image
            input_image = Image.open(uploaded_file)

            # Perform encryption
            encryption_start_time = timeit.default_timer()
            st.session_state.encrypted_image = encrypt_image(input_image, alpha=alpha_value)
            encryption_end_time = timeit.default_timer()

            # Display the encrypted image
            st.image(st.session_state.encrypted_image, caption="Encrypted Image", use_column_width=True)

            # Save the encrypted image as a downloadable link
            download_link = create_download_link(st.session_state.encrypted_image, "Encrypted_Image")
            st.markdown(download_link, unsafe_allow_html=True)

            # Measure encryption time
            encryption_time = encryption_end_time - encryption_start_time
            st.write(f"Encryption Time: {encryption_time} seconds")

        if decrypt_button and st.session_state.encrypted_image is not None:
            # Load the key
            st.write("Attempting to load the key...")
            try:
                with open("encryption_key.txt", 'r') as key_file:
                    encoded_key = key_file.read()
                    decoded_key = base64.b64decode(encoded_key).decode()
                    key = json.loads(decoded_key)

                # Add debugging messages
                st.write("Key loaded successfully.")
                # st.write(f"Key: {key}")

                # Perform decryption
                decryption_start_time = timeit.default_timer()
                decrypted_image = decrypt_image(st.session_state.encrypted_image, key)
                decryption_end_time = timeit.default_timer()

                # Display the decrypted image
                st.image(decrypted_image, caption="Decrypted Image", use_column_width=True)

                # Save the decrypted image as a downloadable link
                download_link = create_download_link(decrypted_image, "Decrypted_Image")
                st.markdown(download_link, unsafe_allow_html=True)

                # Measure decryption time
                decryption_time = decryption_end_time - decryption_start_time
                st.write(f"Decryption Time: {decryption_time} seconds")

            except Exception as e:
                # Display an error message if key loading fails
                st.error(f"Failed to load the key: {str(e)}")

        else:
            st.write("You need to First Encrypt image inorder to Decrypt it")

if __name__ == "__main__":
    main()
