# Main program
import os
import logging as log

from args import parser, process_args
from tasks import get_task
from SSLmodels import get_model
from trainer import Trainer,GANTrainer
from utils import config_logging, load_model, save_model
import torch

def main(args):

    # preparation
    if not os.path.exists(args.exp_dir):
        os.makedirs(args.exp_dir)
    config_logging(os.path.join(args.exp_dir, "%s.log" % args.exp_name))
    log.info("Experiment %s" % (args.exp_name))
    log.info("Receive config %s" % (args.__str__()))
    log.info("Start creating tasks")
    pretrain_task = [get_task(taskname, args) for taskname in args.pretrain_task]
    finetune_tasks = [get_task(taskname, args) for taskname in args.finetune_tasks]
    log.info("Start loading data")

    if args.image_pretrain_obj != "none" or args.view_pretrain_obj != "none":
        for task in pretrain_task:
            task.load_data()
    for task in finetune_tasks:
        task.load_data()

    log.info("Start creating models")
    if len(pretrain_task):
        if args.image_pretrain_obj != "none":
            image_ssl_model = get_model("image_ssl", args)
            log.info("Loaded image ssl model")

        if args.view_pretrain_obj != "none":
            view_ssl_model = get_model("view_ssl", args)
            log.info("Loaded view ssl model")

    if args.finetune_obj != "none": 
        sup_model = get_model("sup", args)
        log.info("Loaded supervised model")

    #if args.load_ckpt != "none":
    #    load_model(model, pretrain_complete_ckpt)

    # pretrain
    if len(pretrain_task):
        if args.image_pretrain_obj != "none":
            image_ssl_model.to(args.device)
            pretrain = Trainer("pretrain", image_ssl_model, pretrain_task[0], args)
            pretrain.train()
            image_pretrain_complete_ckpt = os.path.join(
                args.exp_dir, "image_pretrain_%s_complete.pth" % pretrain_task[0].name
            )
            save_model(image_pretrain_complete_ckpt, image_ssl_model)
        else:
            if args.imagessl_load_ckpt:
                image_pretrain_complete_ckpt = args.imagessl_load_ckpt

        if args.view_pretrain_obj != "none":
            view_ssl_model.to(args.device)
            pretrain = Trainer("pretrain", view_ssl_model, pretrain_task[0], args)
            pretrain.train()
            view_pretrain_complete_ckpt = os.path.join(
                args.exp_dir, "view_pretrain_%s_complete.pth" % pretrain_task[0].name
            )
            save_model(view_pretrain_complete_ckpt, view_ssl_model)
        else:
            if args.viewssl_load_ckpt:
                view_pretrain_complete_ckpt = args.viewssl_load_ckpt

    # finetune and test
    for task in finetune_tasks:
        if args.imagessl_load_ckpt is not "none":
            pretrained_dict = torch.load(image_pretrain_complete_ckpt,map_location=torch.device('cpu'))
            model_dict = sup_model.state_dict()
            tdict = model_dict.copy()
            # print(sup_model.image_network.parameters())
            # print((sup_model.image_network[1].weight.data))
            # wtv = sup_model.image_network[0].weight.data
            # print(tdict.items()==model_dict.items())
            # print(type(tdict),type(model_dict))


            # print(model_dict.keys())
            # print("\n\n\n")

            
            pretrained_dict = {k.replace("patch","image"): v for k, v in pretrained_dict.items() if k.replace("patch","image") in model_dict}
            # print(pretrained_dict.keys())
            # print("\n\n\n")

            model_dict.update(pretrained_dict)
            sup_model.load_state_dict(model_dict)
            # print(type(tdict),type(model_dict))
            # print(sup_model.image_network[1].weight.data)
            # print((tdict.items()==model_dict.items()).all())
            
            


       
        if "adv" in args.finetune_obj:
            # print(type(sup_model))
            sup_model["generator"].to(args.device)
            sup_model["discriminator"].to(args.device)
            finetune = GANTrainer("finetune", sup_model, task, args)
        else:
            sup_model.to(args.device)
            finetune = Trainer("finetune", sup_model, task, args)

        finetune.train()
        finetune.eval("test")
        if "adv" in args.finetune_obj:
            finetune_generator_complete_ckpt = os.path.join(
                    args.exp_dir, "finetune_%s_generator_complete.pth" % task.name
                )

            save_model(finetune_generator_complete_ckpt, sup_model["generator"])

            finetune_discriminator_complete_ckpt = os.path.join(
                    args.exp_dir, "finetune_%s_discriminator_complete.pth" % task.name
                )

            save_model(finetune_discriminator_complete_ckpt, sup_model["discriminator"])
        
        else:
            finetune_complete_ckpt = os.path.join(
                    args.exp_dir, "finetune_%s_complete.pth" % task.name
                )

            save_model(finetune_complete_ckpt, sup_model)
        

    # evaluate
    # TODO: evaluate result on test split, write prediction for leaderboard submission (for dataset
    # without test labels)
    log.info("Done")
    return


if __name__ == "__main__":
    args = parser.parse_args()
    process_args(args)
    main(args)
