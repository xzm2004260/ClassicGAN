from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import matplotlib
matplotlib.use('Agg')
import pathlib
import os
import random
import tensorflow as tf
import numpy as np
from tqdm import tqdm
from Data import roll, channel_num, class_num, input_length
from Model import generator, discriminator, get_noise
#import memory_saving_gradients
# monkey patch tf.gradients to point to our custom version, with automatic
# checkpoint selection
#tf.__dict__["gradients"] = memory_saving_gradients.gradients_memory
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

def main():

    shared_noise_len = 400
    noise_length = 200
    total_train_epoch = 100
    
    with tf.name_scope('inputs'):
        inputs = tf.placeholder(tf.float32, [None, class_num, input_length, channel_num], name='inputs')
        sharednoise = tf.placeholder(tf.float32, [None, shared_noise_len], name='sharednoise')
        noise = tf.placeholder(tf.float32, [channel_num, None, noise_length], name='noise')
        train = tf.placeholder(tf.bool, name='traintest')
    with tf.name_scope('gen'):
        gen = [0] * channel_num
        for i in range(channel_num):
            gen[i] = generator(noise, sharednoise, i, train)
        input_gen = tf.stack(gen, axis=3, name='gen_stack')
    print('generator set')
    with tf.name_scope('dis'):
        dis_real = discriminator(inputs=inputs)
        dis_gene = discriminator(inputs=input_gen, reuse=True)
    print('discriminator set')
    with tf.name_scope('loss'):
        #loss_dis_real =
        #tf.reduce_mean(tf.losses.softmax_cross_entropy(onehot_labels=tf.ones_like(dis_real),
        #logits=dis_real, label_smoothing=0.1), name='loss_dis_real')
        #loss_dis_real =
        #tf.reduce_mean(tf.losses.sigmoid_cross_entropy(multi_class_labels=tf.ones_like(dis_real),
        #logits=dis_real, label_smoothing=0.1), name='loss_dis_real')
        #loss_dis_real =
        #tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=dis_real,
        #labels=tf.ones_like(dis_real)), name='loss_dis_real')
        #loss_dis_gene =
        #tf.reduce_mean(tf.losses.softmax_cross_entropy(onehot_labels=tf.zeros_like(dis_gene),
        #logits=dis_gene, label_smoothing=0.1), name='loss_dis_gene')
        #loss_dis_gene =
        #tf.reduce_mean(tf.losses.sigmoid_cross_entropy(multi_class_labels=label_dis_gene,
        #logits=dis_gene, label_smoothing=0.1), name='loss_dis_gene')
        #loss_dis_gene =
        #tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=dis_gene,
        #labels=tf.zeros_like(dis_gene)), name='loss_dis_gene')
        #loss_dis = loss_dis_real + loss_dis_gene
        loss_dis = -tf.reduce_mean(tf.log(dis_real) + tf.log(1 - dis_gene))
        #loss_gen =
        #tf.reduce_mean(tf.losses.softmax_cross_entropy(onehot_labels=tf.ones_like(dis_gene),
        #logits=dis_gene, label_smoothing=0.1), name='loss_gen')
        #loss_gen =
        #tf.reduce_mean(tf.losses.sigmoid_cross_entropy(multi_class_labels=label_dis_real,
        #logits=dis_gene, label_smoothing=0.1), name='loss_gen')
        #loss_gen =
        #tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=dis_gene,
        #labels=tf.ones_like(dis_gene)), name='loss_gen')
        loss_gen = -tf.reduce_mean(tf.log(dis_gene))
        tf.summary.scalar('discriminator_loss', loss_dis)
        #tf.summary.scalar('loss_dis_real', loss_dis_real)
        #tf.summary.scalar('loss_dis_gene', loss_dis_gene)
        tf.summary.scalar('generator_loss', loss_gen)
    print('loss set')
    dis_var = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='dis')
    gen_var = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='gen')
    with tf.name_scope('optimizers'):
        extra_update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        with tf.control_dependencies(extra_update_ops):
            gen_train = tf.train.AdamOptimizer(learning_rate=0.01).minimize(loss_gen, var_list=gen_var, name='gen_train')
        dis_train = tf.train.GradientDescentOptimizer(learning_rate=0.01).minimize(loss_dis, var_list=dis_var, name='dis_train')
    print('optimizer set')
    loss_val_dis = loss_val_gen = 1.0
    gpu_options = tf.GPUOptions(allow_growth=True)
    config = tf.ConfigProto(allow_soft_placement=True, gpu_options=gpu_options)
    config.gpu_options.allocator_type = 'BFC'
    with tf.Session(config=config) as sess:
        merged = tf.summary.merge_all()
        writer = tf.summary.FileWriter('train', sess.graph)
        sess.run(tf.global_variables_initializer())
        data = []
        pathlist = list(pathlib.Path('Classics').glob('**/*.mid'))
        train_count = 0
        print('preparing complete')
        for epoch in tqdm(range(total_train_epoch)):
            random.shuffle(pathlist)
            for songnum, path in enumerate(tqdm(pathlist)):
                try:
                    length, data = roll(path)
                except:
                    continue
                tqdm.write(str(path))
                n_batch = length // input_length
                batch_input = np.empty([n_batch, class_num, input_length, channel_num])
                for i in range(n_batch):
                    batch_input[i] = data[:, i * input_length:(i + 1) * input_length, :]
                feed_sharednoise = get_noise(n_batch, shared_noise_len)
                feed_noise = np.empty([channel_num, n_batch, noise_length])
                for i in range(channel_num):
                    feed_noise[i] = get_noise(n_batch, noise_length)
                summary, _, loss_val_dis = sess.run([merged, dis_train, loss_dis], feed_dict={inputs: batch_input, noise: feed_noise, sharednoise: feed_sharednoise, train: True})
                writer.add_summary(summary, train_count)
                train_count += 1
                for i in range(10):
                    summary, _, loss_val_gen = sess.run([merged, gen_train, loss_gen], feed_dict={inputs: batch_input, noise: feed_noise, sharednoise: feed_sharednoise, train: True})
                    writer.add_summary(summary, train_count)
                    train_count += 1
                tqdm.write('%06d' % train_count + ' D loss: {:.7}'.format(loss_val_dis) + ' G loss: {:.7}'.format(loss_val_gen))
                if songnum % 1000 == 0:
                    n_batch = 15
                    feed_sharednoise = get_noise(n_batch, shared_noise_len)
                    feed_noise = np.empty([channel_num, n_batch, noise_length])
                    for i in range(channel_num):
                        feed_noise[i] = get_noise(n_batch, noise_length)
                    samples = sess.run([gen], feed_dict={noise: feed_noise, sharednoise: feed_sharednoise, train: False})
                    samples = np.stack(samples)
                    np.save(file='Samples/song_%06d' % (songnum + epoch * len(pathlist)), arr=samples)
        writer.close()
if __name__ == '__main__':
    main()
