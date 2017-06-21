#!/usr/bin/env python
import os
from tensorflow.examples.tutorials.mnist import input_data
from models import *
from utils import *
from common import *


args = parse_args(models.keys())

print args

if len(args.tag) == 0:
    args.tag = 'dcgan'

BASE_FOLDER = 'out_{}/{}_BN{}_LR{}_K{}/'.format(args.tag, args.net, int(args.bn), args.lr, args.kernel)
OUT_FOLDER = os.path.join(BASE_FOLDER, 'out/')
LOG_FOLDER = os.path.join(BASE_FOLDER, 'log/')

if args.net is None:
    args.net = 'simple_cnn'
assert('cnn' in args.net)

def_gen = lambda x, name, **kwargs: models[args.net][0](x, name, k=args.kernel, **kwargs)
def_dis = lambda x, name, **kwargs: models[args.net][1](x, name, 1, k=args.kernel, last_act=tf.sigmoid, **kwargs)
# Added sigmoid so that no 0 values are put into log(x)


LR = args.lr

z0 = tf.placeholder(tf.float32, shape=[None, DIM_Z])
x0 = tf.placeholder(tf.float32, shape=[None, 784])
x1 = tf.reshape(x0, [-1,28,28,1])

global_step = tf.Variable(0, trainable=False)
increment_step = tf.assign_add(global_step, 1)

lr = tf.constant(LR)



### DCGAN
G = def_gen(z0, 'DCGAN_G', bn=args.bn)
D_real = def_dis(x1, 'DCGAN_D', bn=args.bn)
D_fake = def_dis(G, 'DCGAN_D', bn=args.bn, reuse=True)

# Loss functions
D_loss = tf.reduce_mean(-tf.log(D_real)-tf.log(1-D_fake))
G_loss = tf.reduce_mean(-tf.log(D_fake))

D_solver = (tf.train.AdamOptimizer(learning_rate=lr, beta1=0.5))  \
            .minimize(D_loss, var_list=get_trainable_params('DCGAN_D'))
G_solver = (tf.train.AdamOptimizer(learning_rate=lr, beta1=0.5))  \
            .minimize(G_loss, var_list=get_trainable_params('DCGAN_G'))

tf.summary.scalar('DCGAN_D(x)', tf.reduce_mean(D_real))
tf.summary.scalar('DCGAN_D(G)', tf.reduce_mean(D_fake))



# Output images
tf.summary.image('DCGAN', G, max_outputs=3)

# Tensorboard
summaries = tf.summary.merge_all()


# Session
gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.5)
sess = tf.Session(config=tf.ConfigProto(log_device_placement=True, gpu_options=gpu_options))
sess.run(tf.global_variables_initializer())

writer = tf.summary.FileWriter(LOG_FOLDER, sess.graph)

# Initial setup for visualization
outputs = [G]
figs = [None] * len(outputs)
fig_names = ['fig_DCGAN_gen_{:04d}.png']
output_names = ['DCGAN']

if not os.path.exists(OUT_FOLDER):
    os.makedirs(OUT_FOLDER)



saver = tf.train.Saver(get_trainable_params('DCGAN_D') + get_trainable_params('DCGAN_G'))


# Load dataset
data = input_data.read_data_sets('data/mnist/', one_hot=True)

print('{:>10}, {:>7}, {:>7}, {:>7}') \
    .format('Iters', 'cur_LR', 'DCGAN_D', 'DCGAN_G')

# 500 iterations = 1 epoch
N_ITERS_PER_EPOCH = int(50000 / BATCH_SIZE)
N_ITERS = N_ITERS_PER_EPOCH * 100
for it in range(N_ITERS):
    # Train DCGAN
    batch_xs, batch_ys = data.train.next_batch(BATCH_SIZE)

    _, loss_D = sess.run(
            [D_solver, D_loss],
            feed_dict={x0: batch_xs, z0: sample_z(BATCH_SIZE, DIM_Z)}
        )

    _, loss_G = sess.run(
        [G_solver, G_loss],
        feed_dict={z0: sample_z(BATCH_SIZE, DIM_Z)}
    )

    # Increment steps
    _, cur_lr = sess.run([increment_step, lr])

    plt.ion()
    if it % 100 == 0:
        print('{:10d}, {:1.4f}, {: 1.4f}, {: 1.4f}') \
                .format(it, cur_lr, loss_D, loss_G)

        rand_latent = sample_z(16, DIM_Z)

        if it % 1000 == 0:
            for i, output in enumerate(outputs):
                samples = sess.run(output, feed_dict={z0: rand_latent})
                figs[i] = plot(samples, i)
                figs[i].canvas.draw()

                plt.savefig(OUT_FOLDER + fig_names[i].format(it / 1000), bbox_inches='tight')

        # Tensorboard
        cur_summary = sess.run(summaries, feed_dict={x0: batch_xs, z0: rand_latent})
        writer.add_summary(cur_summary, it)

        if it % 10000 == 0:
            saver.save(sess, OUT_FOLDER + 'dcgan', it)

