import os
import random
import sys
from typing import Sequence, Mapping, Any, Union
import torch


def get_value_at_index(obj: Union[Sequence, Mapping], index: int) -> Any:
    """Returns the value at the given index of a sequence or mapping.

    If the object is a sequence (like list or string), returns the value at the given index.
    If the object is a mapping (like a dictionary), returns the value at the index-th key.

    Some return a dictionary, in these cases, we look for the "results" key

    Args:
        obj (Union[Sequence, Mapping]): The object to retrieve the value from.
        index (int): The index of the value to retrieve.

    Returns:
        Any: The value at the given index.

    Raises:
        IndexError: If the index is out of bounds for the object and the object is not a mapping.
    """
    try:
        return obj[index]
    except KeyError:
        return obj["result"][index]


def find_path(name: str, path: str = None) -> str:
    """
    Recursively looks at parent folders starting from the given path until it finds the given name.
    Returns the path as a Path object if found, or None otherwise.
    """
    # If no path is given, use the current working directory
    if path is None:
        path = os.getcwd()

    # Check if the current directory contains the name
    if name in os.listdir(path):
        path_name = os.path.join(path, name)
        print(f"{name} found: {path_name}")
        return path_name

    # Get the parent directory
    parent_directory = os.path.dirname(path)

    # If the parent directory is the same as the current directory, we've reached the root and stop the search
    if parent_directory == path:
        return None

    # Recursively call the function with the parent directory
    return find_path(name, parent_directory)


def add_comfyui_directory_to_sys_path() -> None:
    """
    Add 'ComfyUI' to the sys.path
    """
    comfyui_path = find_path("ComfyUI")
    if comfyui_path is not None and os.path.isdir(comfyui_path):
        sys.path.append(comfyui_path)
        print(f"'{comfyui_path}' added to sys.path")


def add_extra_model_paths() -> None:
    """
    Parse the optional extra_model_paths.yaml file and add the parsed paths to the sys.path.
    """
    try:
        from main import load_extra_path_config
    except ImportError:
        print(
            "Could not import load_extra_path_config from main.py. Looking in utils.extra_config instead."
        )
        from utils.extra_config import load_extra_path_config

    extra_model_paths = find_path("extra_model_paths.yaml")

    if extra_model_paths is not None:
        load_extra_path_config(extra_model_paths)
    else:
        print("Could not find the extra_model_paths config file.")


add_comfyui_directory_to_sys_path()
add_extra_model_paths()


def import_custom_nodes() -> None:
    """Find all custom nodes in the custom_nodes folder and add those node objects to NODE_CLASS_MAPPINGS

    This function sets up a new asyncio event loop, initializes the PromptServer,
    creates a PromptQueue, and initializes the custom nodes.
    """
    import asyncio
    import execution
    from nodes import init_extra_nodes
    import server

    # Creating a new event loop and setting it as the default loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Creating an instance of PromptServer with the loop
    server_instance = server.PromptServer(loop)
    execution.PromptQueue(server_instance)

    # Initializing custom nodes
    init_extra_nodes()


from nodes import NODE_CLASS_MAPPINGS


def main():
    import_custom_nodes()
    with torch.inference_mode():
        loadimage = NODE_CLASS_MAPPINGS["LoadImage"]()
        loadimage_3 = loadimage.load_image(image="Frame 84.png")

        controlnetloader = NODE_CLASS_MAPPINGS["ControlNetLoader"]()
        controlnetloader_5 = controlnetloader.load_controlnet(
            control_net_name="SDXL\controlnet-canny-sdxl-1.0\diffusion_pytorch_model_V2.safetensors"
        )

        ttn_pipeloadersdxl_v2 = NODE_CLASS_MAPPINGS["ttN pipeLoaderSDXL_v2"]()
        ttn_pipeloadersdxl_v2_6 = ttn_pipeloadersdxl_v2.sdxl_pipeloader(
            ckpt_name="artium_v20Turboboosted.safetensors",
            config_name="Default",
            vae_name="xlVAEC_c0.safetensors",
            clip_skip=-2,
            loras="",
            refiner_ckpt_name="None",
            refiner_config_name="Default",
            positive_g="pixel art, round plush, melting plush, plush wearing pajama, ribbon, clothes are dragging on the floor, fluffy blankets, side view, soft colors, (soft lighting:1.4), soft shading, white background, simple background",
            positive_l="pixel art, round plush, melting plush, plush wearing pajama, ribbon, clothes are dragging on the floor, fluffy blankets, side view, soft colors, (soft lighting:1.4), soft shading, white background, simple background",
            negative_g="hand, arm, foot, (outline:1.4), particles",
            negative_l="hand, arm, foot, (outline:1.4), particles",
            conditioning_aspect="1x Empty Latent Aspect",
            conditioning_width=2048,
            conditioning_height=2048,
            crop_width=0,
            crop_height=0,
            target_aspect="1x Empty Latent Aspect",
            target_width=1024,
            target_height=1024,
            positive_ascore=6,
            negative_ascore=2,
            empty_latent_aspect="1024 x 1024 [S] 1:1",
            empty_latent_width=1024,
            empty_latent_height=1024,
            batch_size=1,
            seed=random.randint(1, 2**64),
        )

        loadimage_16 = loadimage.load_image(image="Frame 87.png")

        vaeencode = NODE_CLASS_MAPPINGS["VAEEncode"]()
        vaeencode_11 = vaeencode.encode(
            pixels=get_value_at_index(loadimage_16, 0),
            vae=get_value_at_index(ttn_pipeloadersdxl_v2_6, 4),
        )

        loadimagemask = NODE_CLASS_MAPPINGS["LoadImageMask"]()
        loadimagemask_35 = loadimagemask.load_image(
            image="Frame 82ㄴㅇㄻㅇㄴㅁㄹㄴㅁㄴ (4).png", channel="alpha"
        )

        ttn_seed = NODE_CLASS_MAPPINGS["ttN seed"]()
        ttn_seed_46 = ttn_seed.plant(seed=random.randint(1, 2**64))

        controlnetapplyadvanced = NODE_CLASS_MAPPINGS["ControlNetApplyAdvanced"]()
        controlnetapplyadvanced_2 = controlnetapplyadvanced.apply_controlnet(
            strength=1,
            start_percent=0,
            end_percent=1,
            positive=get_value_at_index(ttn_pipeloadersdxl_v2_6, 2),
            negative=get_value_at_index(ttn_pipeloadersdxl_v2_6, 3),
            control_net=get_value_at_index(controlnetloader_5, 0),
            image=get_value_at_index(loadimage_3, 0),
        )

        setlatentnoisemask = NODE_CLASS_MAPPINGS["SetLatentNoiseMask"]()
        setlatentnoisemask_34 = setlatentnoisemask.set_mask(
            samples=get_value_at_index(vaeencode_11, 0),
            mask=get_value_at_index(loadimagemask_35, 0),
        )

        latentupscaleby = NODE_CLASS_MAPPINGS["LatentUpscaleBy"]()
        latentupscaleby_49 = latentupscaleby.upscale(
            upscale_method="nearest-exact",
            scale_by=1,
            samples=get_value_at_index(setlatentnoisemask_34, 0),
        )

        repeatlatentbatch = NODE_CLASS_MAPPINGS["RepeatLatentBatch"]()
        repeatlatentbatch_32 = repeatlatentbatch.repeat(
            amount=4, samples=get_value_at_index(latentupscaleby_49, 0)
        )

        ttn_pipeksamplersdxl_v2 = NODE_CLASS_MAPPINGS["ttN pipeKSamplerSDXL_v2"]()
        ttn_pipeksamplersdxl_v2_7 = ttn_pipeksamplersdxl_v2.sample(
            lora_name="Pixel_Xl_V1 .safetensors",
            lora_strength=1,
            upscale_method="None",
            upscale_model_name="None",
            factor=2,
            rescale="by percentage",
            percent=50,
            width=1024,
            height=1024,
            longer_side=1024,
            crop="disabled",
            base_steps=6,
            cfg=3,
            denoise=0.6,
            refiner_steps=20,
            refiner_cfg=8,
            refiner_denoise=1,
            sampler_name="dpmpp_sde",
            scheduler="karras",
            image_output="Hide",
            save_prefix="ComfyUI",
            file_type="png",
            embed_workflow=True,
            seed=random.randint(1, 2**64),
            sdxl_pipe=get_value_at_index(ttn_pipeloadersdxl_v2_6, 0),
            optional_positive=get_value_at_index(controlnetapplyadvanced_2, 0),
            optional_negative=get_value_at_index(controlnetapplyadvanced_2, 1),
            optional_latent=get_value_at_index(repeatlatentbatch_32, 0),
        )

        vaeencode_39 = vaeencode.encode(
            pixels=get_value_at_index(ttn_pipeksamplersdxl_v2_7, 11),
            vae=get_value_at_index(ttn_pipeksamplersdxl_v2_7, 9),
        )

        loadimagemask_43 = loadimagemask.load_image(
            image="Frame 82ㄴㅇㄻㅇㄴㅁㄹㄴㅁㄴ123.png", channel="alpha"
        )

        aio_preprocessor = NODE_CLASS_MAPPINGS["AIO_Preprocessor"]()
        k_centroid_auto_downscale = NODE_CLASS_MAPPINGS["K-Centroid Auto Downscale"]()
        saveimage = NODE_CLASS_MAPPINGS["SaveImage"]()
        invertmask = NODE_CLASS_MAPPINGS["InvertMask"]()

        for q in range(1):
            aio_preprocessor_4 = aio_preprocessor.execute(
                preprocessor="FakeScribblePreprocessor",
                resolution=512,
                image=get_value_at_index(loadimage_3, 0),
            )

            k_centroid_auto_downscale_13 = k_centroid_auto_downscale.downscale(
                centroids=1, image=get_value_at_index(ttn_pipeksamplersdxl_v2_7, 11)
            )

            saveimage_14 = saveimage.save_images(
                filename_prefix="ComfyUI",
                images=get_value_at_index(k_centroid_auto_downscale_13, 0),
            )

            invertmask_36 = invertmask.invert(
                mask=get_value_at_index(loadimagemask_35, 0)
            )

            setlatentnoisemask_45 = setlatentnoisemask.set_mask(
                samples=get_value_at_index(vaeencode_39, 0),
                mask=get_value_at_index(loadimagemask_43, 0),
            )


if __name__ == "__main__":
    main()
