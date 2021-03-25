---
title: "Why Bitcoin Has Failed and the Future of Payment Cryptos"
author: x4e
keywords: [cryptocurrency,bitcoin,nano,bitcoin cash]
description: "A criticism of Bitcoin and an evaluation of it's competitors"
date: 4th February 2021
---

Bitcoin's white paper presents it as a "peer-to-peer electronic cash system", however I do not believe that Bitcoin has fulfilled the requirements of cash.

## The problems with Bitcoin

Firstly, here is the absolute minimum I expect out of a form of cash:

* Widely recognized as being of value
* Irreversible transactions
* Easy to hold reasonable amounts
* Hard to forge (transactions and balances)
* Easy and fast to transfer reasonable amounts

Each of these are satisfied by my local fiat, GBP, however they are not all satisfied by Bitcoin:

* Bitcoin is recognized as being of value nowadays, this is satisfied
* Bitcoin transactions cannot be reversed (at least certainly after they have been accepted into a block)
* Vast amounts of Bitcoin are easily held
* It is impractical to forge transactions and balances are impossible to forged
* While it is easy to transfer Bitcoin, it is certainly not fast. The current average time between blocks is just over 9 minutes, and your transaction will only be in the next block if you pay the most competitive fee.

Bitcoin was designed before cryptocurrencies had ever received any major attention: Satoshi did not imagine, prepare or test for the amount of pressure that is currently being exerted on the system. It was only long after Satoshi last went offline that Bitcoin began to be picked up by major media outlets and normal people began to here about it.

In 2017/2018 Bitcoin experienced parabolic growth and attention, causing the network to come under extreme strain from the amount and size of transactions taking place. A combination of huge fees and transaction waiting times highlighted the impracticality of Bitcoin as a form of cash and probably contributed to it's price decline, since back then Bitcoin's price speculation was based on it being a form of payment rather than a store of value.

The technical reason behind Bitcoin's lack of scalability is the block size. Every transaction is included in a block which is then committed to the blockchain, larger blocks allow more transactions to be processed at a time. When Bitcoin was created there was actually no intention to have a block size limit, but one did effectively exist due to some related code. Satoshi manually added a 1 MB block size limit in 2010 which became effective in 2013 after the unintended block size limit was removed.

There are some reasons why a larger block size could not be desirable:

* It can require all nodes to be able to process blocks up to the largest size, this increases the hardware requirement of running a node, therefore making nodes less common and more likely to be owned by the big mining companies
* Fewer nodes would reduce miner competition and more expensive to run nodes would increase costs, both potentially leading to higher fees
* The network could be subject to denial of service attacks if large blocks are continuously forced through the network


## Bitcoin Cash

Bitcoin Cash (BCH) was created as a hard fork of Bitcoin in 2017, with its first change being an upgrade to an 8 MB maximum block size. This was intended to be a solution to Bitcoin's scalability.

Since the fork, Bitcoin Cash itself has hard forked multiple times, splitting the community into Bitcoin Cash Node (BCH/BCHN), Bitcoin Cash ABC (BCHA), and Bitcoin Satoshi's Vision (BSV), with Bitcoin Cash Node having the majority consensus and as such retaining the BCH tickers. 

Each of these forks have split the community and developers, and many communities still call the minority forks Bitcoin Cash, creating a lot of confusion. For example, [bitcoincash.org](https://www.bitcoincash.org/) seems to promote BCH however it is operated by BCHA and leads users to BCHA services.

Decentralized currencies only work when consensus can be reached. Because of this split, unclear, and disagreeing community I do not have much hope for the future of BCH and I do not hold any.


## Nano

Nano was created under the name RaiBlocks (XRB) in 2014/15. Nano uses a block lattice to give each account its own blockchain, with each transaction being its own block. Since there are multiple blockchains, transactions on each blockchain can be performed asynchronously. 

Nano also does not have every node validating blocks, instead users vote with their account balance for a representative who will perform validation for them. Representatives do not gain any monetary reward, resulting in a more decentralized network as nodes are typically run by individuals rather than large mining companies. This also allows transactions to have 0 fees.

Nano has an average transaction confirmation time of 0.2 seconds and has succeeded tests of handling up to 1800 transactions per second (compared to bitcoin's 3-4).


## Conclusion

Many currencies have tried to improve upon Bitcoin, like Bitcoin Cash and Nano. These don't seem to have gained as much attention as the Ethereum competitors have recently, but they will still have a large effect on the future of CryptoCurrencies. Bitcoin Cash attempts to build upon Bitcoin's design by making tweaks to components such as the block size, whereas Nano is an entirely new protocol designed to be asynchronous, fast and fee-less.
